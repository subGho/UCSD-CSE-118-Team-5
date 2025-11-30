#!/usr/bin/env python3
"""
Combine ultrasonic and break beam readings to infer door_opened and walked_through,
then POST to weatherApp when both are true within a short time window.
"""

import statistics
import time
from collections import deque

import requests
import RPi.GPIO as GPIO

# GPIO pins (BCM numbering)
TRIG_PIN = 23
ECHO_PIN = 24
BREAKBEAM_PIN = 22

# Tuning parameters
DISTANCE_THRESHOLD_CM = 35.0          # Distance that separates open/closed state
STD_DEV_HIGH = 5.0                    # What qualifies as "high" standard deviation
EVENT_WINDOW_SEC = 2.0                # How long two events can be apart and still count together
POST_COOLDOWN_SEC = 5.0               # Avoid duplicate posts too quickly
SAMPLE_DELAY_SEC = 0.1                # Main loop sleep between samples

POST_URL = "http://localhost:8000/weather"
POST_PAYLOAD = {
    "userId": "subhon",
    "doorStatus": "Open",
    "walkThroughStatus": "True",
    "indoorTemp": "68",
}


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.setup(BREAKBEAM_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.output(TRIG_PIN, GPIO.LOW)


def measure_distance():
    """Return a single distance measurement in cm, or -1 on timeout/error."""
    GPIO.output(TRIG_PIN, GPIO.LOW)
    time.sleep(0.00002)  # 20 µs settle

    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)  # 10 µs pulse
    GPIO.output(TRIG_PIN, GPIO.LOW)

    timeout = 0.1
    start_wait = time.time()
    while GPIO.input(ECHO_PIN) == GPIO.LOW:
        if time.time() - start_wait > timeout:
            return -1

    pulse_start = time.time()
    start_wait = pulse_start
    while GPIO.input(ECHO_PIN) == GPIO.HIGH:
        if time.time() - start_wait > timeout:
            return -1

    pulse_end = time.time()
    duration = pulse_end - pulse_start
    distance = (duration * 34300) / 2  # cm
    return distance


def send_post():
    try:
        resp = requests.post(POST_URL, json=POST_PAYLOAD, timeout=5)
        resp.raise_for_status()
        print(f"POST sent. Response: {resp.status_code} {resp.text}")
        return True
    except requests.exceptions.RequestException as exc:
        print(f"Failed to send POST: {exc}")
        return False


def main():
    setup_gpio()
    distance_history = deque(maxlen=15)
    door_opened = False
    walked_through = False
    door_opened_at = 0.0
    walked_through_at = 0.0
    last_post_time = 0.0

    try:
        while True:
            distance = measure_distance()
            if distance > 0:
                distance_history.append(distance)

            if len(distance_history) >= 2:
                std_dev = statistics.stdev(distance_history)
            else:
                std_dev = 0.0

            if std_dev >= STD_DEV_HIGH and distance > 0:
                if distance > DISTANCE_THRESHOLD_CM:
                    if not door_opened:
                        print(f"Door opened (distance {distance:.2f} cm, std {std_dev:.2f})")
                    door_opened = True
                    door_opened_at = time.time()
                else:
                    if door_opened:
                        print(f"Door closed (distance {distance:.2f} cm, std {std_dev:.2f})")
                    door_opened = False
                    door_opened_at = time.time()

            beam_broken = GPIO.input(BREAKBEAM_PIN) == GPIO.LOW
            if beam_broken:
                if not walked_through:
                    print("Beam broken")
                walked_through = True
                walked_through_at = time.time()
            else:
                walked_through = False

            now = time.time()
            door_recent = door_opened and (now - door_opened_at) <= EVENT_WINDOW_SEC
            walk_recent = walked_through and (now - walked_through_at) <= EVENT_WINDOW_SEC

            if door_recent and walk_recent and (now - last_post_time) >= POST_COOLDOWN_SEC:
                if send_post():
                    last_post_time = now

            time.sleep(SAMPLE_DELAY_SEC)

    except KeyboardInterrupt:
        print("\nStopping due to keyboard interrupt.")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")


if __name__ == "__main__":
    main()
