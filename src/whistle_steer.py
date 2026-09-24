"""Live whistle spectrogram that steers the robot over MQTT.

Listens to the microphone, shows a scrolling spectrogram of 1500-2500 Hz, and
marks the loudest frequency in each frame. That frequency is turned into a
steering value and published to the motor server (see motor_server.py):

  1500 Hz -> steer -1.0  (full left)
  2000 Hz -> steer  0.0  (straight)
  2500 Hz -> steer  1.0  (full right)

In between, steering is linear: steer = (freq - 2000) / 500.

A frame only counts as a whistle when the peak is at least --threshold dB
above the median level of the band. When you stop whistling, steer 0 is sent
once so the robot goes straight again. Steering is only published when the
value changes (rounded to 0.01).

Running
-------
  python src/whistle_steer.py
  python src/whistle_steer.py --threshold 20 --topic Dan_Codrin_Robot

Close the plot window or press Ctrl+C to quit. This script only sends steer;
send drive separately (e.g. mosquitto_pub -t Dan_Codrin_Robot/drive -m 0.4).
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
import paho.mqtt.client as mqtt
import pyaudio
from matplotlib.animation import FuncAnimation

from motor_server import DEFAULT_TOPIC
from mqtt_client import BROKER_HOST, BROKER_PORT

RATE = 44100
CHUNK = 2048          # samples per frame: ~46 ms, ~21.5 Hz per FFT bin
HISTORY_SECONDS = 5   # width of the scrolling spectrogram
F_MIN, F_MAX = 1500, 2500
F_CENTER = (F_MIN + F_MAX) / 2
F_HALF_RANGE = (F_MAX - F_MIN) / 2


def freq_to_steer(freq):
    """Map a frequency in [F_MIN, F_MAX] linearly to a steer value in [-1, 1]."""
    return max(-1.0, min(1.0, (freq - F_CENTER) / F_HALF_RANGE))


class WhistleSteer:
    def __init__(self, host, port, topic, threshold):
        self.topic = f"{topic.rstrip('/')}/steer"
        self.threshold = threshold
        self.last_sent = None

        freqs = np.fft.rfftfreq(CHUNK, 1 / RATE)
        self.band = (freqs >= F_MIN) & (freqs <= F_MAX)
        self.band_freqs = freqs[self.band]
        self.window = np.hanning(CHUNK)

        n_frames = int(HISTORY_SECONDS * RATE / CHUNK)
        self.spec = np.full((len(self.band_freqs), n_frames), -100.0)  # dB, newest column on the right
        self.peaks = np.full(n_frames, np.nan)  # peak frequency per frame, NaN = no whistle

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(host, port)
        self.client.loop_start()
        print(f"[mqtt] publishing steering to {self.topic} on {host}:{port}")

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                                      input=True, frames_per_buffer=CHUNK)

    def process_frame(self, samples):
        """FFT one frame, update the history, and return the peak frequency (or None)."""
        spectrum = np.abs(np.fft.rfft(samples * self.window))[self.band]
        db = 20 * np.log10(spectrum + 1e-9)

        peak_idx = int(np.argmax(db))
        is_whistle = db[peak_idx] - np.median(db) >= self.threshold
        peak_freq = float(self.band_freqs[peak_idx]) if is_whistle else None

        self.spec = np.roll(self.spec, -1, axis=1)
        self.spec[:, -1] = db
        self.peaks = np.roll(self.peaks, -1)
        self.peaks[-1] = peak_freq if is_whistle else np.nan
        return peak_freq

    def send_steer(self, peak_freq):
        steer = round(freq_to_steer(peak_freq), 2) if peak_freq is not None else 0.0
        if steer != self.last_sent:
            self.client.publish(self.topic, str(steer), qos=1)
            self.last_sent = steer
        return steer

    def run(self):
        fig, ax = plt.subplots(figsize=(10, 5))
        extent = (-HISTORY_SECONDS, 0, F_MIN, F_MAX)
        image = ax.imshow(self.spec, origin="lower", aspect="auto", extent=extent,
                          cmap="magma", vmin=-20, vmax=60)
        times = np.linspace(-HISTORY_SECONDS, 0, len(self.peaks))
        (peak_line,) = ax.plot(times, self.peaks, "c.", markersize=4, label="loudest frequency")
        (current,) = ax.plot([], [], "o", color="lime", markersize=12, label="current steering")
        ax.axhline(F_CENTER, color="white", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")
        ax.legend(loc="upper left")
        fig.colorbar(image, ax=ax, label="Amplitude (dB)")

        # Right axis shows the steering value each frequency maps to
        steer_ax = ax.secondary_yaxis("right", functions=(freq_to_steer_unclamped, steer_to_freq))
        steer_ax.set_ylabel("Steer (-1 left, +1 right)")

        def update(_):
            # Drain every frame that arrived since the last redraw so we never fall behind
            peak_freq = None
            available = max(self.stream.get_read_available() // CHUNK, 1)
            for _ in range(available):
                raw = self.stream.read(CHUNK, exception_on_overflow=False)
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                peak_freq = self.process_frame(samples)

            steer = self.send_steer(peak_freq)
            image.set_data(self.spec)
            peak_line.set_ydata(self.peaks)
            if peak_freq is not None:
                current.set_data([0], [peak_freq])
                ax.set_title(f"Whistle {peak_freq:.0f} Hz  ->  steer {steer:+.2f}")
            else:
                current.set_data([], [])
                ax.set_title("No whistle  ->  steer 0.00")
            return image, peak_line, current

        self._animation = FuncAnimation(fig, update, interval=20, blit=False, cache_frame_data=False)
        plt.show()

    def close(self):
        self.client.publish(self.topic, "0.0", qos=1).wait_for_publish(timeout=2)
        self.client.disconnect()
        self.client.loop_stop()
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()


def freq_to_steer_unclamped(freq):
    return (freq - F_CENTER) / F_HALF_RANGE


def steer_to_freq(steer):
    return steer * F_HALF_RANGE + F_CENTER


def main():
    parser = argparse.ArgumentParser(description="Steer the robot by whistling between 1500 and 2500 Hz.")
    parser.add_argument("--host", default=BROKER_HOST, help=f"MQTT broker (default {BROKER_HOST})")
    parser.add_argument("--port", type=int, default=BROKER_PORT, help=f"MQTT port (default {BROKER_PORT})")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help=f"motor server base topic (default {DEFAULT_TOPIC})")
    parser.add_argument("--threshold", type=float, default=15,
                        help="dB the peak must be above the band median to count as a whistle (default 15)")
    args = parser.parse_args()

    app = WhistleSteer(args.host, args.port, args.topic, args.threshold)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.close()


if __name__ == "__main__":
    main()
