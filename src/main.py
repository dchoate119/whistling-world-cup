"""Drive the robot by whistling: one laptop whistles throttle, the other steering.

  --role throttle  (connected to the robot) pitch sets speed: F_MIN slow, F_MAX full
  --role steer     pitch steers: F_MIN full left, middle straight, F_MAX full right,
                   sent to the throttle laptop over MQTT on <ROBOT_TOPIC>/steer
  No whistle     -> that input goes to 0 (after SILENCE_STOP_S, so short gaps don't twitch)
  Ctrl+C         -> stop and disconnect

  python src/main.py --role throttle
  python src/main.py --role steer
  python src/main.py --role steer --threshold 30   # same flag as spectrogram.py
  python src/main.py --role steer --plot           # also show the live spectrogram
"""

import argparse
import time

from audio import Microphone, PitchDetector
from config import F_MAX, F_MIN, ROBOT_TOPIC, WHISTLE_THRESHOLD_DB
from mqtt_client import GameMQTT
from robot import Robot

MIN_DRIVE = 0.2        # throttle speed at F_MIN, 0..1; F_MAX is full speed
SILENCE_STOP_S = 0.3   # seconds of silence before stopping


def pitch_to_steer(freq):
    """Map F_MIN..F_MAX linearly to steer -1..1."""
    center = (F_MIN + F_MAX) / 2
    half_range = (F_MAX - F_MIN) / 2
    return max(-1.0, min(1.0, (freq - center) / half_range))


def pitch_to_drive(freq):
    """Map F_MIN..F_MAX linearly to drive MIN_DRIVE..1."""
    return MIN_DRIVE + (1 - MIN_DRIVE) * (pitch_to_steer(freq) + 1) / 2


def main():
    parser = argparse.ArgumentParser(description="Drive the robot by whistling.")
    parser.add_argument("--role", choices=["throttle", "steer"], required=True,
                        help="throttle: this laptop drives the robot; steer: sends steer to it over MQTT")
    parser.add_argument("--threshold", type=float, default=WHISTLE_THRESHOLD_DB,
                        help=f"dB the peak must be above the band median to count as a whistle "
                             f"(default {WHISTLE_THRESHOLD_DB})")
    parser.add_argument("--plot", action="store_true", help="also show the live spectrogram")
    args = parser.parse_args()

    steer = 0.0  # latest steer from MQTT (used by throttle)

    def on_steer(message):
        nonlocal steer
        steer = float(message)

    link = GameMQTT(topic=f"{ROBOT_TOPIC}/steer", on_message=on_steer)
    link.connect()
    robot = Robot() if args.role == "throttle" else None
    last_whistle = 0.0
    value = sent = 0.0  # this laptop's drive or steer, and the last steer published

    def on_frame(freq):
        nonlocal last_whistle, value, sent
        if freq is not None:
            last_whistle = time.monotonic()
            value = pitch_to_drive(freq) if robot else round(pitch_to_steer(freq), 1)
        elif time.monotonic() - last_whistle > SILENCE_STOP_S:
            value = 0.0
        if robot:
            robot.move(value, steer)
        elif value != sent:
            link.publish(str(value))
            sent = value

    try:
        if args.plot:
            import spectrogram
            spectrogram.main(on_frame)  # reads --threshold itself; returns when the window closes
        else:
            mic = Microphone()
            detector = PitchDetector(args.threshold)
            try:
                while True:
                    for samples in mic.read_available():
                        on_frame(detector.analyze(samples)[1])
            finally:
                mic.close()
    except KeyboardInterrupt:
        pass
    finally:
        if robot:
            robot.close()
        else:
            link.publish("0.0").wait_for_publish(1)  # don't leave the robot turning
        link.disconnect()


if __name__ == "__main__":
    main()
