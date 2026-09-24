"""Shared settings: MQTT broker and topics, robot hardware, and audio."""

# MQTT broker
# TODO: confirm broker with instructor
BROKER_HOST = "test.mosquitto.org"
BROKER_PORT = 1883

# Topics
GAME_TOPIC = "ME193/Rogers"  # game messages: start / FAILED / GOAL

# Connection Card on our Double Motor
CARD_COLOR = "yellow"
CARD_SERIAL = "0994"  # string: keeps the leading zero

# Audio
MIC_NAME = "AB13X USB Audio" # use the first input device whose name contains this; None = system default
RATE = 44100
CHUNK = 2048                # samples per frame: ~46 ms, ~21.5 Hz per FFT bin
F_MIN, F_MAX = 1500, 2500   # whistle band (Hz)
WHISTLE_THRESHOLD_DB = 35   # peak must be this far above the band median to count as a whistle
