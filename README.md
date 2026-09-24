# whistling-world-cup
Audio control for mobile soccer robots

Whistle pitch drives a LEGO Education robot. Robots play as **ball** or **goalie**, coordinated over MQTT.

## Rules
- Game begins when `start` is received on `ME193/Rogers`.
- **Ball caught:** goalie comes close to the ball's front-facing color sensor → ball stops, publishes `FAILED`, plays death song. Goalie plays success song.
- **Goal:** ball whistles special command → publishes `GOAL`, plays success song. Goalie plays death song.

## Stack
- `legoeducation` (BLE): `DoubleMotor`, `ColorSensor`
- `pyaudio` + `numpy`: audio capture and pitch detection
- `paho-mqtt`: game messages
- Conda env: `lego` OR virtual env

## File structure
```
config.py        # broker, topic, messages, thresholds, device names
audio.py         # mic stream + pitch detection
controls.py      # pitch → command (speed, steer, stop, goal)
robot.py         # DoubleMotor + ColorSensor (drive, proximity)
mqtt_client.py   # connect, subscribe, publish
songs.py         # death / success beep sequences
main.py          # role selection + game loop
```

## Checklist

### Hardware
- [ ] Connect to `DoubleMotor` and `ColorSensor`
- [ ] Mount color sensor open and facing forward
- [ ] Calibrate `reflection` threshold for goalie proximity

### Audio
- [ ] Pitch detection
- [ ] Define whistle control scheme (speed, steering, stop)
- [ ] Define special goal command
- [ ] Map pitch to motor commands

### MQTT
- [ ] Subscribe to `ME193/Rogers`, wait for `start`
- [ ] Publish `FAILED` / `GOAL`
- [ ] React to opponent's messages

### Game logic
- [ ] Role selection (`ball` / `goalie`)
- [ ] Ball: stop on proximity, publish `FAILED`, play death song
- [ ] Ball: publish `GOAL` on goal command, play success song
- [ ] Goalie: play success song on `FAILED`, death song on `GOAL`
- [ ] Death and success songs (`beep` sequences)

### Testing
- [ ] Full game run against another robot
