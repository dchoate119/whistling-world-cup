"""Shared settings: MQTT broker and topics, robot hardware, and audio."""

# MQTT broker
# TODO: confirm broker with instructor
BROKER_HOST = "test.mosquitto.org"
BROKER_PORT = 1883

# Topics
GAME_TOPIC = "ME193/Rogers"  # game messages: start / FAILED / GOAL
ROBOT_TOPIC = "Dan_Codrin_Robot"  # between our laptops: <base>/steer

# Connection Card on our Double Motor and Color Sensor (same card)
CARD_COLOR = "yellow"
CARD_SERIAL = "0994"  # string: keeps the leading zero
CAUGHT_REFLECTION = 30  # ball: color sensor reflection % at or above this = goalie caught us; tune with python src/robot.py

# Audio
MIC_NAME = "AB13X USB Audio" # use the first input device whose name contains this; None = system default
RATE = 44100
CHUNK = 2048                # samples per frame: ~46 ms, ~21.5 Hz per FFT bin
THROTTLE_BAND = (1500, 1900)  # throttle laptop: low = full backward, high = full forward
DEAD_ZONE = 0.1               # throttle: |drive| below this (±20 Hz around the middle) counts as stopped
STEER_BAND = (2100, 2400)     # steer laptop: lower half = 45° left turn, upper half = 45° right turn
TURN_DEG = 45                 # degrees per turn, measured by the motor's IMU
GOAL_F = 2500                 # throttle laptop: whistle at or above this = goal command (ball)
F_MIN, DETECT_MAX = 1450, 3200  # detector listens from F_MIN up to DETECT_MAX (below THROTTLE_BAND so its edge shows)
WHISTLE_THRESHOLD_DB = 35   # peak must be this far above the band median to count as a whistle
MIN_LEVEL_DB = 110            # peak must also be at least this loud (absolute dB; depends on mic gain). 0 = off
