"""LEGO Double Motor (+ optional Color Sensor): connect, then drive with drive/steer in [-1, 1].

  robot = Robot()
  robot.move(0.5, 0.2)   # half speed, gentle right curve
  robot.close()
  python src/robot.py    # prints the color sensor's reflection, for tuning CAUGHT_REFLECTION

How drive and steer combine (arcade mixing):
  left  = drive + steer
  right = drive - steer
If either side exceeds 1, both are scaled down together so the turn is kept.

  drive  steer   left  right   result
   1.0    0.0    100   100     straight forward
   1.0    1.0    100     0     forward, pivot right around the right wheel
   0.5    0.2     70    30     gentle right curve at half speed
   0.0    1.0    100  -100     spin in place to the right
  -1.0    0.0   -100  -100     straight backward
"""

import time

import legoeducation as le

from config import CARD_COLOR, CARD_SERIAL


def mix(drive, steer):
    """Arcade mix drive/steer in [-1, 1] into (left, right) in [-1, 1]."""
    left = drive + steer
    right = drive - steer
    biggest = max(abs(left), abs(right), 1.0)
    return left / biggest, right / biggest


class Robot:
    def __init__(self, card_color=CARD_COLOR, card_serial=CARD_SERIAL, max_speed=100, sensor=False):
        self.max_speed = max_speed  # motor speed % at drive=1
        self._last = None
        self.motor = le.DoubleMotor()
        print(f"[robot] searching for Double Motor with {card_color} card {card_serial}...")
        self.motor.connect(card_color=getattr(le, f"LEGO_COLOR_{card_color.upper()}"), card_serial=card_serial)
        if not self.motor.connected:
            raise RuntimeError(f"Could not connect to the Double Motor with {card_color} card {card_serial} "
                               "(is it on and in range?)")
        print("[robot] connected")
        self.sensor = None
        if sensor:  # ball only: the front color sensor that detects the goalie
            self.sensor = le.ColorSensor()
            print(f"[robot] searching for Color Sensor with {card_color} card {card_serial}...")
            self.sensor.connect(card_color=getattr(le, f"LEGO_COLOR_{card_color.upper()}"), card_serial=card_serial)
            if not self.sensor.connected:
                raise RuntimeError(f"Could not connect to the Color Sensor with {card_color} card {card_serial} "
                                   "(is it on and in range?)")
            print("[robot] color sensor connected")

    def move(self, drive, steer=0.0):
        """Set the motors. Only sends a command when the output changes."""
        left, right = mix(drive, steer)
        output = (round(left * self.max_speed), round(right * self.max_speed))
        if output == self._last:
            return
        if output == (0, 0):
            self.motor.movement_stop()
        else:
            self.motor.movement_move_tank(*output)
        print(f"[robot] left={output[0]:4d}%  right={output[1]:4d}%")
        self._last = output

    def stop(self):
        self.move(0.0, 0.0)

    def yaw(self):
        """Heading in degrees from the motor's IMU (the library refreshes it ~10x per second)."""
        return self.motor.imu_device.yaw

    def reflection(self):
        """Color sensor reflection %: higher = something closer (the library refreshes it ~10x per second)."""
        return self.sensor.sensor.reflection

    def close(self):
        if self.motor.connected:
            self.motor.movement_stop()
            self.motor.disconnect()
        if self.sensor and self.sensor.connected:
            self.sensor.disconnect()
        print("[robot] stopped")


if __name__ == "__main__":
    # Tuning: print the color sensor's reflection; bring the goalie close to pick CAUGHT_REFLECTION
    robot = Robot(sensor=True)
    try:
        while True:
            print(f"reflection {robot.reflection()}%")
            time.sleep(0.2)
    except KeyboardInterrupt:
        robot.close()
