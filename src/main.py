"""Drive the robot by whistling: one laptop whistles throttle, the other steering.

  --role throttle  (connected to the robot) F_MIN full backward, middle stopped, F_MAX full forward
                   --game ball|goalie: waits for "start" on GAME_TOPIC, then plays that part
  --role steer    pitch steers: F_MIN full left, middle straight, F_MAX full right,
                   sent to the throttle laptop over MQTT on <ROBOT_TOPIC>/steer
  Whistle >= GOAL_F -> robot stands still; ball: held GOAL_HOLD_S = goal (publish GOAL, win song)
  No whistle     -> that input goes to 0 (after SILENCE_STOP_S, so short gaps don't twitch)
  Ctrl+C         -> stop and disconnect

  python src/main.py --role throttle --game ball
  python src/main.py --role steer
  python src/main.py --role steer --threshold 30   # same flag as spectrogram.py
  python src/main.py --role steer --plot           # also show the live spectrogram
"""

import argparse
import time

from audio import Microphone, PitchDetector
import songs
from config import F_MAX, F_MIN, GOAL_F, MIN_LEVEL_DB, ROBOT_TOPIC, WHISTLE_THRESHOLD_DB
from mqtt_client import GameMQTT
from robot import Robot

DEAD_ZONE = 0.1        # throttle: |drive| below this (±50 Hz around the middle) counts as stopped
SILENCE_STOP_S = 0.3   # seconds of silence before stopping
GOAL_HOLD_S = 0.7      # ball: seconds of goal whistle before it counts


def pitch_to_steer(freq):
    """Map F_MIN..F_MAX linearly to steer -1..1."""
    center = (F_MIN + F_MAX) / 2
    half_range = (F_MAX - F_MIN) / 2
    return max(-1.0, min(1.0, (freq - center) / half_range))


def pitch_to_drive(freq):
    """Same map as steer (F_MIN full back, F_MAX full forward), but 0 inside the dead zone."""
    drive = pitch_to_steer(freq)
    return drive if abs(drive) >= DEAD_ZONE else 0.0


def main():
    parser = argparse.ArgumentParser(description="Drive the robot by whistling.")
    parser.add_argument("--role", choices=["throttle", "steer"], required=True,
                        help="throttle: this laptop drives the robot; steer: sends steer to it over MQTT")
    parser.add_argument("--game", choices=["ball", "goalie"], help="throttle only: our part this round")
    parser.add_argument("--threshold", type=float, default=WHISTLE_THRESHOLD_DB,
                        help=f"dB the peak must be above the band median to count as a whistle "
                             f"(default {WHISTLE_THRESHOLD_DB})")
    parser.add_argument("--min-level", type=float, default=MIN_LEVEL_DB,
                        help=f"absolute dB the peak must reach (default {MIN_LEVEL_DB}, 0 = off)")
    parser.add_argument("--plot", action="store_true", help="also show the live spectrogram")
    args = parser.parse_args()
    if args.role == "throttle" and not args.game:
        parser.error("--role throttle needs --game ball or --game goalie")

    steer = 0.0  # latest steer from MQTT (used by throttle)

    def on_steer(message):
        nonlocal steer
        steer = float(message)

    link = GameMQTT(topic=f"{ROBOT_TOPIC}/steer", on_message=on_steer)
    link.connect()
    robot = Robot() if args.role == "throttle" else None
    last_whistle = 0.0
    goal_since = None   # when the current goal whistle began
    value = sent = 0.0  # this laptop's drive or steer, and the last steer published
    state = "waiting"   # throttle: waiting -> playing -> over
    heard = None        # goalie: FAILED or GOAL from the ball

    def on_game(message):
        nonlocal state, heard
        if message == "start":
            state, heard = "playing", None
            print("[game] start")
        elif args.game == "goalie" and message in ("FAILED", "GOAL"):
            heard = message

    game = GameMQTT(on_message=on_game) if robot else None  # GAME_TOPIC
    if game:
        game.connect()

    def end(song, message=None):
        """Game over: stop, publish our result if we're the ball, play our song."""
        nonlocal state
        state = "over"
        robot.stop()
        if message:
            game.publish(message)
        print(f"[game] over: {message or heard}")
        songs.play(robot.motor, song)

    def on_frame(freq):
        nonlocal last_whistle, goal_since, value, sent
        now = time.monotonic()
        if freq is not None:
            last_whistle = now
            if freq >= GOAL_F:  # goal command, not driving: stand still
                goal_since = goal_since or now
                value = 0.0
            else:
                goal_since = None
                value = pitch_to_drive(freq) if robot else round(pitch_to_steer(freq), 1)
        elif now - last_whistle > SILENCE_STOP_S:
            goal_since = None
            value = 0.0
        if robot:
            if state == "playing" and heard:  # goalie: the ball says how it ended
                end(songs.WIN if heard == "FAILED" else songs.LOSE)
            elif state == "playing" and args.game == "ball" and goal_since and now - goal_since >= GOAL_HOLD_S:
                end(songs.WIN, "GOAL")
            # TODO: ball caught -> end(songs.LOSE, "FAILED") once the color sensor is on
            robot.move(value if state == "playing" else 0.0, steer)
        elif value != sent:
            link.publish(str(value))
            sent = value

    try:
        if args.plot:
            import spectrogram
            spectrogram.main(on_frame)  # reads --threshold/--min-level itself; returns when the window closes
        else:
            mic = Microphone()
            detector = PitchDetector(args.threshold, args.min_level)
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
        if game:
            game.disconnect()


if __name__ == "__main__":
    main()
