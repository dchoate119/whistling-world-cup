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
python src/main.py             # whistle to drive: pitch steers, silence stops
python src/spectrogram.py      # live view of your whistle pitch, for tuning
```

## File structure
All code is in `src/`. Files marked *planned* don't exist yet.
```
config.py        # broker, topic, card color/serial, audio settings
audio.py         # Microphone (mic stream) + PitchDetector (loudest whistle frequency)
robot.py         # Robot: DoubleMotor drive/steer (ColorSensor + songs planned)
mqtt_client.py   # GameMQTT: connect, subscribe, publish on ME193/Rogers
main.py          # whistle → drive/steer (role selection + game loop planned)
spectrogram.py   # tuning tool: live whistle spectrogram
```

## Checklist

### Hardware
- [x] Connect to `DoubleMotor`
- [ ] Connect to `ColorSensor`
- [ ] Mount color sensor open and facing forward
- [ ] Calibrate `reflection` threshold for goalie proximity

### Audio
- [x] Pitch detection
- [x] First control scheme: whistle = forward + pitch steers, silence = stop
- [ ] Test and tune on the floor (speed, steering, stop delay)
- [ ] Define special goal command
- [x] Map pitch to motor commands

### Code structure
- [x] `config.py`, `audio.py`, `robot.py` (motor), `main.py` (whistle driving)

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
