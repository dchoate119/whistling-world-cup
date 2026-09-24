"""MQTT connection for game messages (start / FAILED / GOAL)."""

import threading
import uuid

import paho.mqtt.client as mqtt

# TODO: move to config.py once broker is confirmed with instructor
BROKER_HOST = "test.mosquitto.org"
BROKER_PORT = 1883
TOPIC = "ME193/Rogers"


class GameMQTT:
    def __init__(self, host=BROKER_HOST, port=BROKER_PORT, topic=TOPIC, on_message=None):
        self.host = host
        self.port = port
        self.topic = topic
        self.on_message = on_message  # callback(message: str)
        self._connected = threading.Event()

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"whistle-{uuid.uuid4().hex[:8]}",
        )
        self.client.on_connect = self._handle_connect
        self.client.on_disconnect = self._handle_disconnect
        self.client.on_message = self._handle_message

    def connect(self, timeout=10):
        """Connect and start the network loop in a background thread."""
        self.client.connect(self.host, self.port)
        self.client.loop_start()
        if not self._connected.wait(timeout):
            raise TimeoutError(f"Could not connect to {self.host}:{self.port}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, message):
        self.client.publish(self.topic, message)

    def _handle_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[mqtt] connect failed: {reason_code}")
            return
        # Subscribe here so we resubscribe after a reconnect
        client.subscribe(self.topic)
        self._connected.set()
        print(f"[mqtt] connected to {self.host}:{self.port}, subscribed to {self.topic}")

    def _handle_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected.clear()
        print(f"[mqtt] disconnected: {reason_code}")

    def _handle_message(self, client, userdata, msg):
        message = msg.payload.decode(errors="replace").strip()
        print(f"[mqtt] received: {message}")
        if self.on_message:
            self.on_message(message)


if __name__ == "__main__":
    # Manual test: prints incoming messages, publishes whatever you type
    game = GameMQTT()
    game.connect()
    try:
        while True:
            game.publish(input())
    except (KeyboardInterrupt, EOFError):
        game.disconnect()
