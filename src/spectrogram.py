"""Live whistle spectrogram for tuning.

Shows a scrolling spectrogram of the whistle band (F_MIN-DETECT_MAX in config.py)
and marks the loudest frequency in each frame that counts as a whistle. Use it
to see what pitch you are whistling and to pick --threshold for the room.
The status line shows the peak's absolute level, for picking --min-level.

  python src/spectrogram.py
  python src/spectrogram.py --role throttle   # only that laptop's band and actions
  python src/spectrogram.py --threshold 20 --min-level 90

Close the plot window or press Ctrl+C to quit.
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

from audio import Microphone, PitchDetector
from config import (CHUNK, DEAD_ZONE, DETECT_MAX, F_MIN, GOAL_F, MIN_LEVEL_DB, RATE, STEER_BAND, THROTTLE_BAND,
                    TURN_DEG, WHISTLE_THRESHOLD_DB)

HISTORY_SECONDS = 5  # width of the scrolling spectrogram


def action(freq, role=None):
    """What a whistle at freq does, as main.py maps it; role None = either laptop. "" = nothing."""
    if freq is None:
        return ""
    if STEER_BAND[0] <= freq <= STEER_BAND[1]:
        if role == "throttle":
            return ""  # the throttle laptop ignores the steer band
        return f"{'Left' if freq < sum(STEER_BAND) / 2 else 'Right'} turn {TURN_DEG}°"
    if role == "steer":
        return ""  # the steer laptop only hears its own band
    if freq >= GOAL_F:
        return "Goal"
    if not THROTTLE_BAND[0] <= freq <= THROTTLE_BAND[1]:
        return ""  # between the bands: neither laptop reacts
    drive = (freq - sum(THROTTLE_BAND) / 2) / ((THROTTLE_BAND[1] - THROTTLE_BAND[0]) / 2)  # -1..1, like main.py
    if abs(drive) < DEAD_ZONE:
        return "Stop"  # main.py's dead zone
    return f"{'Forward' if drive > 0 else 'Backward'} {abs(drive):.0%}"


def main(on_frame=None):
    parser = argparse.ArgumentParser(description="Live whistle spectrogram.")
    parser.add_argument("--threshold", type=float, default=WHISTLE_THRESHOLD_DB,
                        help=f"dB the peak must be above the band median to count as a whistle "
                             f"(default {WHISTLE_THRESHOLD_DB})")
    parser.add_argument("--min-level", type=float, default=MIN_LEVEL_DB,
                        help=f"absolute dB the peak must reach (default {MIN_LEVEL_DB}, 0 = off)")
    parser.add_argument("--role", choices=["throttle", "steer"],
                        help="only show that laptop's band and actions (main.py passes its own --role)")
    args = parser.parse_known_args()[0]  # ignore main.py's --plot

    detector = PitchDetector(args.threshold, args.min_level)
    n_frames = int(HISTORY_SECONDS * RATE / CHUNK)
    spec = np.zeros((len(detector.band_freqs), n_frames))  # dB above band median, newest column on the right
    peaks = np.full(n_frames, np.nan)  # peak frequency per frame, NaN = no whistle

    fig, ax = plt.subplots(figsize=(10, 5))
    image = ax.imshow(spec, origin="lower", aspect="auto", extent=(-HISTORY_SECONDS, 0, F_MIN, DETECT_MAX),
                      cmap="magma", vmin=0, vmax=45)
    (peak_line,) = ax.plot(np.linspace(-HISTORY_SECONDS, 0, n_frames), peaks, "c.", markersize=4)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    bands = ((THROTTLE_BAND, "white", "throttle"), (STEER_BAND, "lime", "steer"))
    band_lines = [ax.axhline(f, color=color, linestyle="--", linewidth=1)  # control band edges for this role
                  for band, color, role in bands if args.role in (None, role) for f in band]
    if args.role in (None, "throttle"):  # forward / backward split
        band_lines.append(ax.axhline(sum(THROTTLE_BAND) / 2, color="white", linestyle=":", linewidth=1))
    if args.role in (None, "steer"):  # left / right split
        band_lines.append(ax.axhline(sum(STEER_BAND) / 2, color="lime", linestyle=":", linewidth=1))
    if args.role:  # which laptop this is, in big letters above the plot
        ax.set_title({"throttle": "THROTTLE", "steer": "STEERING"}[args.role], fontsize=20, weight="bold")
    fig.colorbar(image, ax=ax, label="dB above band median")
    # Status inside the axes: the title sits outside them, so updating it would defeat blitting
    status = ax.text(0.01, 0.97, "", transform=ax.transAxes, color="white", va="top")
    label = ax.text(0.99, 0.97, "", transform=ax.transAxes, color="white", va="top", ha="right",
                    fontsize=20, weight="bold")  # what the whistle is doing right now

    mic = Microphone()

    def update(_):
        nonlocal spec, peaks
        peak_freq = None
        for samples in mic.read_available():
            db, peak_freq = detector.analyze(samples)
            if on_frame:
                on_frame(peak_freq)
            spec = np.roll(spec, -1, axis=1)
            # Relative to the median, like the detector: the noise floor sits near 0 whatever the mic gain
            spec[:, -1] = db - np.median(db)
            peaks = np.roll(peaks, -1)
            peaks[-1] = np.nan if peak_freq is None else peak_freq

        image.set_data(spec)
        peak_line.set_ydata(peaks)
        status.set_text(("No whistle" if peak_freq is None else f"Whistle {peak_freq:.0f} Hz")
                        + f"   peak {db.max():.0f} dB")
        label.set_text(action(peak_freq, args.role))
        return image, *band_lines, peak_line, status, label  # redrawn every frame, in this order (lines over image)

    anim = FuncAnimation(fig, update, interval=20, blit=True, cache_frame_data=False)  # must stay referenced or it stops
    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        mic.close()


if __name__ == "__main__":
    main()
