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
python src/motor_server.py     # laptop with Bluetooth to the robot
python src/whistle_steer.py    # laptop with the mic: whistle 1500–2500 Hz to steer
mosquitto_pub -h test.mosquitto.org -t Dan_Codrin_Robot/drive -m 0.4   # drive is still manual
```
The two scripts only talk over MQTT, so they can run on the same laptop or different ones.

## File structure
All code is in `src/`. Files marked *planned* don't exist yet.
```
config.py        # broker, topics, card color/serial, audio settings
audio.py         # Microphone (mic stream) + PitchDetector (loudest whistle frequency)
controls.py      # planned: pitch → command (speed, steer, stop, goal)
robot.py         # planned: DoubleMotor + ColorSensor (drive, proximity)
mqtt_client.py   # GameMQTT: connect, subscribe, publish on ME193/Rogers
songs.py         # planned: death / success beep sequences
main.py          # planned: role selection + game loop

motor_server.py  # testing tool: MQTT drive/steer → DoubleMotor
whistle_steer.py # testing tool: whistle pitch → MQTT steer, with live spectrogram
```

## Checklist

### Hardware
- [x] Connect to `DoubleMotor`
- [ ] Connect to `ColorSensor`
- [ ] Mount color sensor open and facing forward
- [ ] Calibrate `reflection` threshold for goalie proximity

### Audio
- [x] Pitch detection
- [ ] Define whistle control scheme (speed, steering, stop)
- [ ] Define special goal command
- [ ] Map pitch to motor commands (steering done, speed/stop not yet)

### Code structure
- [x] `config.py`, `audio.py`
- [ ] `controls.py`, `robot.py`, `songs.py`, `main.py`

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
