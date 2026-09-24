"""Drive the robot by whistling.

  Whistle        -> drive forward at DRIVE, pitch steers:
                    F_MIN full left, middle straight, F_MAX full right
  No whistle     -> stop (after SILENCE_STOP_S, so short gaps don't twitch)
  Ctrl+C         -> stop and disconnect

  python src/main.py
"""

import time

from audio import Microphone, PitchDetector
from config import F_MAX, F_MIN
from robot import Robot

DRIVE = 0.5            # forward speed while whistling, 0..1
SILENCE_STOP_S = 0.3   # seconds of silence before stopping


def pitch_to_steer(freq):
    """Map F_MIN..F_MAX linearly to steer -1..1."""
    center = (F_MIN + F_MAX) / 2
    half_range = (F_MAX - F_MIN) / 2
    return max(-1.0, min(1.0, (freq - center) / half_range))


def main():
    robot = Robot()
    mic = Microphone()
    detector = PitchDetector()
    last_whistle = 0.0
    try:
        while True:
            for samples in mic.read_available():
                _, freq = detector.analyze(samples)
                if freq is not None:
                    last_whistle = time.monotonic()
                    robot.move(DRIVE, pitch_to_steer(freq))
                elif time.monotonic() - last_whistle > SILENCE_STOP_S:
                    robot.stop()
    except KeyboardInterrupt:
        pass
    finally:
        mic.close()
        robot.close()


if __name__ == "__main__":
    main()
