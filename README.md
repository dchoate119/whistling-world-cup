# whistling-world-cup
Audio control for mobile soccer robots

Whistle pitch drives a LEGO Education robot. Robots play as **ball** or **goalie**, coordinated over MQTT.

## Rules
- Game begins when `start` is received on `ME193/Rogers`.
- **Ball caught:** goalie comes close to the ball's front-facing color sensor → ball stops, publishes `FAILED`, plays death song. Goalie plays success song.
- **Goal:** ball whistles special command → publishes `GOAL`, plays success song. Goalie plays death song.

## Game flow (throttle laptop)
```
python src/main.py --role throttle --game ball|goalie
   main.py: main() reads the flags, then connects:
     robot.py        Robot()                   → Bluetooth to the motor (+ color sensor if ball)
     mqtt_client.py  GameMQTT(".../steer")     → steer values from the other laptop
     mqtt_client.py  GameMQTT(ME193/Rogers)    → game messages
        ↓
wait for "start"
   mqtt_client.py receives a message → calls main.py on_game()
   on_game: "start" → state = "playing"
   until then, on_frame() keeps sending robot.move(0) → robot stays still
        ↓
drive by whistling  (repeats ~20 times per second)
   audio.py   Microphone      → one chunk of sound
   audio.py   PitchDetector   → loudest pitch, or None
   main.py    on_frame(freq):
                1500–1900 Hz → drive speed (pitch_to_drive): below 1700 backward, above forward
                               (1450–1500 still heard = full backward)
                ≥ 2500 Hz    → stand still, start the goal timer
                (steer laptop: 2100–2400 Hz → one 45° turn per whistle, low half left, high half right;
                 the robot steers until the IMU yaw has moved 45°, while still following the throttle)
                silence      → stop
   robot.py   Robot.move(drive, steer)   → motors
        ↓
BALL                                         GOALIE
 goal timer reaches 0.7 s (on_frame)          on_game() hears "FAILED" or "GOAL"
   → end(songs.WIN, "GOAL")                      → only saves it in `heard`
 robot.reflection() ≥ CAUGHT_REFLECTION        next on_frame() sees `heard`
   → end(songs.LOSE, "FAILED")                    → end(songs.WIN or songs.LOSE)
        ↓
end()  (main.py)
   state = "over"
   robot.py        Robot.stop()
   mqtt_client.py  publish GOAL / FAILED   (ball only)
   songs.py        play(robot.motor, song) → beeps on the motor
        ↓
game over: on_frame() keeps sending move(0) until the next "start"
```
`on_frame()` is the heartbeat: the only place the robot gets commands. MQTT messages arrive on a
background thread, so `on_game()` just flips `state` / `heard` and the next `on_frame()` acts on it.
The steer laptop only runs the audio part of `on_frame()` and publishes steer; it never touches the
game topic or the robot.

## Stack
- `legoeducation` (BLE): `DoubleMotor`, `ColorSensor`
- `pyaudio` + `numpy`: audio capture and pitch detection
- `paho-mqtt`: game messages
- `matplotlib`: live spectrogram (debug)
- Conda env: `lego` OR virtual env

## Setup
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running (current)
```
python src/main.py --role throttle --game ball     # laptop connected to the robot (or --game goalie)
                                                   # low backward, high forward, silence stops, ≥2500 Hz held = goal
python src/main.py --role steer      # other laptop: 2100–2400 Hz whistle = one 45° IMU turn (low left, high right), sent over MQTT
python src/main.py --role steer --plot   # either role, plus the live spectrogram for troubleshooting
python src/spectrogram.py      # live view of your whistle pitch, for tuning
python src/spectrogram.py --role throttle   # only that laptop's band lines and action label
```

## File structure
All code is in `src/`.
```
config.py        # broker, topic, card color/serial, audio settings
audio.py         # Microphone (mic stream) + PitchDetector (loudest whistle frequency)
robot.py         # Robot: DoubleMotor drive/steer + IMU yaw, ColorSensor reflection (ball); run it to tune the sensor
songs.py         # win/lose songs + play() on the motor's beeper
mqtt_client.py   # GameMQTT: connect, subscribe, publish on ME193/Rogers
main.py          # whistle → drive/steer, ball/goalie game loop
spectrogram.py   # tuning tool: live whistle spectrogram with band lines and action label (Forward / Left turn / Goal…)
```

## Checklist

### Hardware
- [x] Connect to `DoubleMotor`
- [x] Connect to `ColorSensor`
- [ ] Mount color sensor open and facing forward
- [ ] Calibrate `reflection` threshold for goalie proximity

### Audio
- [x] Pitch detection
- [x] Two-laptop control: throttle 1500–1900 Hz (forward/backward), steer 2100–2400 Hz (45° IMU turns), silence = stop
- [ ] Test and tune on the floor (speed, `TURN_STEER` / `TURN_DEG` overshoot, stop delay)
- [x] Define special goal command (whistle ≥ 2500 Hz for 0.7 s)
- [x] Map pitch to motor commands

### Code structure
- [x] `config.py`, `audio.py`, `robot.py` (motor), `main.py` (whistle driving)

### MQTT
- [x] Subscribe to `ME193/Rogers`, wait for `start`
- [x] Publish `FAILED` / `GOAL`
- [x] React to opponent's messages

### Game logic
- [x] Role selection (`ball` / `goalie`)
- [x] Ball: stop on proximity, publish `FAILED`, play death song
- [x] Ball: publish `GOAL` on goal command, play success song
- [x] Goalie: play success song on `FAILED`, death song on `GOAL`
- [x] Death and success songs (`beep` sequences)

### Testing
- [ ] Full game run against another robot
