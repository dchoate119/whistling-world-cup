"""MQTT motor server: drive a LEGO Education Double Motor from MQTT commands.

Runs until Ctrl+C. Connects over Bluetooth to the Double Motor with the yellow
Connection Card 0994 (change with --card-color / --card-serial), subscribes to
two command topics, and continuously applies the latest values to the motors.

Commands
--------
Each command is its own topic. The payload is a single number as plain text.

  <base>/drive   -1.0 .. 1.0   Forward/backward throttle.
                                 1.0 = full speed forward
                                 0.0 = no forward/backward motion
                                -1.0 = full speed backward

  <base>/steer   -1.0 .. 1.0   Turning.
                                -1.0 = turn fully left
                                 0.0 = straight
                                 1.0 = turn fully right

  <base>/stop    (any payload)  Sets drive and steer to 0 and stops the motors.

<base> defaults to "Dan_Codrin_Robot" (change with --topic). Out-of-range
values are clamped to [-1, 1]; payloads that aren't numbers are ignored.

drive and steer are independent and stick until changed: sending steer=0.5
keeps the current drive. The server remembers the latest of each.

How drive and steer combine (arcade mixing)
-------------------------------------------
  left  = drive + steer
  right = drive - steer
If either side exceeds 1, both are scaled down together so the ratio (and
therefore the turn) is kept. Each side is then multiplied by --max-speed
(percent, default 100) and sent to the motor.

  drive  steer   left  right   result
   1.0    0.0    100   100     straight forward
   1.0    1.0    100     0     forward, pivot right around the right wheel
   0.5    0.2     70    30     gentle right curve at half speed
   0.0    1.0    100  -100     spin in place to the right
  -1.0    0.0   -100  -100     straight backward

Sending commands
----------------
With the mosquitto clients:
  mosquitto_pub -h test.mosquitto.org -t Dan_Codrin_Robot/drive -m 0.5
  mosquitto_pub -h test.mosquitto.org -t Dan_Codrin_Robot/steer -m -0.3
  mosquitto_pub -h test.mosquitto.org -t Dan_Codrin_Robot/stop  -m ""

From Python:
  import paho.mqtt.publish as publish
  publish.single("Dan_Codrin_Robot/drive", "0.5", hostname="test.mosquitto.org")

Running the server
------------------
  python src/motor_server.py
  python src/motor_server.py --card-color red --card-serial 1234
  python src/motor_server.py --topic Dan_Codrin_Ball --max-speed 60 --timeout 1
"""

import argparse
import math
import threading
import time

import legoeducation as le
import paho.mqtt.client as mqtt

from config import BROKER_HOST, BROKER_PORT, CARD_COLOR, CARD_SERIAL, ROBOT_TOPIC

UPDATE_HZ = 20  # how often the motor output is refreshed


CARD_COLORS = sorted(
    n[len("LEGO_COLOR_"):].lower() for n in dir(le)
    if n.startswith("LEGO_COLOR_") and n not in ("LEGO_COLOR_HEX_MAP", "LEGO_COLOR_NAME_MAP", "LEGO_COLOR_NOCOLOR")
)


def mix(drive, steer):
    """Arcade mix drive/steer in [-1, 1] into (left, right) in [-1, 1]."""
    left = drive + steer
    right = drive - steer
    biggest = max(abs(left), abs(right), 1.0)
    return left / biggest, right / biggest


class MotorServer:
    def __init__(self, host, port, topic, max_speed, timeout, card_color, card_serial):
        self.host = host
        self.port = port
        self.topic = topic.rstrip("/")
        self.max_speed = max_speed
        self.timeout = timeout  # seconds without a command before stopping; 0 = never
        self.card_color = card_color
        self.card_serial = card_serial

        # Latest commands, written by the MQTT thread and read by the main loop
        self._lock = threading.Lock()
        self.drive = 0.0
        self.steer = 0.0
        self.last_command = time.monotonic()

        self.motor = le.DoubleMotor()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._handle_connect
        self.client.on_message = self._handle_message

    def run(self):
        print(f"[motor] searching for Double Motor with {self.card_color} card {self.card_serial}...")
        color = getattr(le, f"LEGO_COLOR_{self.card_color.upper()}")
        self.motor.connect(card_color=color, card_serial=self.card_serial)
        if not self.motor.connected:
            raise RuntimeError(
                f"Could not connect to the Double Motor with {self.card_color} card {self.card_serial} "
                "(is it on and in range?)"
            )
        print("[motor] connected")

        self.client.connect(self.host, self.port)
        self.client.loop_start()

        # Motor commands are sent only from this thread, never from MQTT callbacks
        last_output = None
        try:
            while True:
                with self._lock:
                    drive, steer = self.drive, self.steer
                    idle = time.monotonic() - self.last_command

                if self.timeout and idle > self.timeout:
                    drive = steer = 0.0

                left, right = mix(drive, steer)
                output = (round(left * self.max_speed), round(right * self.max_speed))
                if output != last_output:
                    if output == (0, 0):
                        self.motor.movement_stop()
                    else:
                        self.motor.movement_move_tank(*output)
                    print(f"[motor] left={output[0]:4d}%  right={output[1]:4d}%")
                    last_output = output

                time.sleep(1 / UPDATE_HZ)
        finally:
            self.client.disconnect()
            self.client.loop_stop()
            if self.motor.connected:
                self.motor.movement_stop()
                self.motor.disconnect()
            print("[motor] stopped")

    def _handle_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[mqtt] connect failed: {reason_code}")
            return
        # Subscribe here so we resubscribe after a reconnect
        client.subscribe(f"{self.topic}/+", qos=1)
        print(f"[mqtt] connected to {self.host}:{self.port}, listening on {self.topic}/{{drive,steer,stop}}")

    def _handle_message(self, client, userdata, msg):
        command = msg.topic.rsplit("/", 1)[-1]
        payload = msg.payload.decode(errors="replace").strip()

        if command == "stop":
            with self._lock:
                self.drive = self.steer = 0.0
                self.last_command = time.monotonic()
            print("[mqtt] stop")
            return
        if command not in ("drive", "steer"):
            return

        try:
            value = float(payload)
        except ValueError:
            print(f"[mqtt] ignoring {command}: {payload!r} is not a number")
            return
        if math.isnan(value):
            print(f"[mqtt] ignoring {command}: NaN")
            return
        clamped = max(-1.0, min(1.0, value))
        if clamped != value:
            print(f"[mqtt] {command} {value} out of range, clamped to {clamped}")

        with self._lock:
            setattr(self, command, clamped)
            self.last_command = time.monotonic()
        print(f"[mqtt] {command} = {clamped}")


def main():
    parser = argparse.ArgumentParser(description="Drive a LEGO Double Motor from MQTT drive/steer commands.")
    parser.add_argument("--host", default=BROKER_HOST, help=f"MQTT broker (default {BROKER_HOST})")
    parser.add_argument("--port", type=int, default=BROKER_PORT, help=f"MQTT port (default {BROKER_PORT})")
    parser.add_argument("--topic", default=ROBOT_TOPIC, help=f"base topic (default {ROBOT_TOPIC})")
    parser.add_argument("--max-speed", type=int, default=100, help="motor speed %% at drive=1 (1-100, default 100)")
    parser.add_argument("--timeout", type=float, default=0,
                        help="stop the motors if no command arrives for this many seconds (default 0 = never)")
    parser.add_argument("--card-color", default=CARD_COLOR, choices=CARD_COLORS,
                        help=f"Connection Card color (default {CARD_COLOR})")
    parser.add_argument("--card-serial", default=CARD_SERIAL,
                        help=f"Connection Card number (default {CARD_SERIAL})")
    args = parser.parse_args()
    if not 1 <= args.max_speed <= 100:
        parser.error("--max-speed must be between 1 and 100")

    server = MotorServer(args.host, args.port, args.topic, args.max_speed, args.timeout,
                         args.card_color, args.card_serial)
    try:
        server.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
