"""Live whistle spectrogram for tuning.

Shows a scrolling spectrogram of the whistle band (F_MIN-F_MAX in config.py)
and marks the loudest frequency in each frame that counts as a whistle. Use it
to see what pitch you are whistling and to pick --threshold for the room.

  python src/spectrogram.py
  python src/spectrogram.py --threshold 20

Close the plot window or press Ctrl+C to quit.
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

from audio import Microphone, PitchDetector
from config import CHUNK, F_MAX, F_MIN, RATE, WHISTLE_THRESHOLD_DB

HISTORY_SECONDS = 5  # width of the scrolling spectrogram


def main():
    parser = argparse.ArgumentParser(description="Live whistle spectrogram.")
    parser.add_argument("--threshold", type=float, default=WHISTLE_THRESHOLD_DB,
                        help=f"dB the peak must be above the band median to count as a whistle "
                             f"(default {WHISTLE_THRESHOLD_DB})")
    args = parser.parse_args()

    detector = PitchDetector(args.threshold)
    n_frames = int(HISTORY_SECONDS * RATE / CHUNK)
    spec = np.zeros((len(detector.band_freqs), n_frames))  # dB above band median, newest column on the right
    peaks = np.full(n_frames, np.nan)  # peak frequency per frame, NaN = no whistle

    fig, ax = plt.subplots(figsize=(10, 5))
    image = ax.imshow(spec, origin="lower", aspect="auto", extent=(-HISTORY_SECONDS, 0, F_MIN, F_MAX),
                      cmap="magma", vmin=0, vmax=45)
    (peak_line,) = ax.plot(np.linspace(-HISTORY_SECONDS, 0, n_frames), peaks, "c.", markersize=4)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    fig.colorbar(image, ax=ax, label="dB above band median")
    # Status inside the axes: the title sits outside them, so updating it would defeat blitting
    status = ax.text(0.01, 0.97, "", transform=ax.transAxes, color="white", va="top")

    mic = Microphone()

    def update(_):
        nonlocal spec, peaks
        peak_freq = None
        for samples in mic.read_available():
            db, peak_freq = detector.analyze(samples)
            spec = np.roll(spec, -1, axis=1)
            # Relative to the median, like the detector: the noise floor sits near 0 whatever the mic gain
            spec[:, -1] = db - np.median(db)
            peaks = np.roll(peaks, -1)
            peaks[-1] = np.nan if peak_freq is None else peak_freq

        image.set_data(spec)
        peak_line.set_ydata(peaks)
        status.set_text("No whistle" if peak_freq is None else f"Whistle {peak_freq:.0f} Hz")
        return image, peak_line, status

    anim = FuncAnimation(fig, update, interval=20, blit=True, cache_frame_data=False)  # must stay referenced or it stops
    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        mic.close()


if __name__ == "__main__":
    main()
