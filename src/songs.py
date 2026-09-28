"""Win and lose songs, played on the motor's beeper.

  songs.play(robot.motor, songs.WIN)
  python src/songs.py   # plays both, for tuning
"""

import time

# Note frequencies (Hz). All below F_MIN so the mic doesn't hear them as whistles. REST = silence.
REST = 0
C4, Eb4, E4, F4, Fs4, G4, Ab4, A4, Bb4, B4 = 262, 311, 330, 349, 370, 392, 415, 440, 466, 494
C5, E5, G5, C6 = 523, 659, 784, 1047

# Songs: (note, seconds)
WIN = [
    (G4, 0.15), (C5, 0.15), (E5, 0.15), (G5, 0.3), (E5, 0.15), (G5, 0.6),  # "Charge!" bugle call
    (REST, 0.25),
    (C5, 0.1), (E5, 0.1), #(G5, 0.1), (C6, 0.1), (REST, 0.05),              # victory run up
    (G5, 0.1), *[(C6, 0.15)] * 10,                                           # ...and rattle the top
]
LOSE = [
    (C5, 0.07), (B4, 0.07), (Bb4, 0.07), (A4, 0.07), (Ab4, 0.07), (G4, 0.07),  # fast slide down
    (REST, 0.3),
    (G4, 0.4), (REST, 0.05), (Fs4, 0.4), (REST, 0.05), (F4, 0.4), (REST, 0.05),  # wah, wah, wah...
    *[(E4, 0.08), (Eb4, 0.08)] * 6,                                            # ...wahhh (wobble)
    (REST, 0.2), (C4, 0.5),                                                    # thud
]


def play(motor, song):
    for freq, seconds in song:
        # Every beep is a short fixed blip (no held tones); `seconds` is the gap before the next note
        if freq:  # REST = just wait
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
