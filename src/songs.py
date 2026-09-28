"""Win and lose songs, played on the motor's beeper.

  songs.play(robot.motor, songs.WIN)
  python src/songs.py   # plays both, for tuning
"""

import time

# (frequency Hz, seconds until next note). Kept below F_MIN so the mic doesn't hear them as whistles.
WIN = [(523, 0.1), (659, 0.2), (784, 0.3), (1047, 0.4)]   # C E G C, rising
LOSE = [(392, 0.1), (370, 0.2), (349, 0.3), (330, 0.4)]   # G F# F E, falling


def play(motor, song):
    for freq, seconds in song:
        # A beep lasts ~1 s and the motor ignores new beeps until it ends, so cut each one short
        motor.beep(frequency=freq, blocking=False)
        time.sleep(seconds)
        motor.stop_beep(blocking=False)


if __name__ == "__main__":
    from robot import Robot

    robot = Robot()
    play(robot.motor, WIN)
    time.sleep(1)
    play(robot.motor, LOSE)
    robot.close()
