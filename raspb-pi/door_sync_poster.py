#!/usr/bin/env python3
"""
Combine ultrasonic and break beam readings to infer door_opened and walked_through,
then POST to weatherApp when both are true within a short time window.
"""

import statistics
import time
from collections import deque

import adafruit_dht
import board
import requests
import RPi.GPIO as GPIO

# GPIO pins (BCM numbering)
TRIG_PIN = 23
ECHO_PIN = 24
BREAKBEAM_PIN = 22

# Tuning parameters
DISTANCE_THRESHOLD_CM = 35.0          # Distance that separates open/closed state
STD_DEV_HIGH = 5.0                    # What qualifies as "high" standard deviation
EVENT_WINDOW_SEC = 5.0                # How long two events can be apart and still count together
POST_COOLDOWN_SEC = 5.0               # Avoid duplicate posts too quickly
SAMPLE_DELAY_SEC = 0.1                # Main loop sleep between samples
DOOR_STABILITY_COUNT = 3              # Number of consistent readings to accept a door state change
DOOR_TRANSITION_COOLDOWN_SEC = 1.0    # Minimum time between door state changes

POST_URL = "http://localhost:8000/weather"
POST_PAYLOAD_OPEN_NOT_WALKED = {
    "userId": "subhon",
    "doorStatus": "Open",
    "walkThroughStatus": "False",
    "indoorTemp": "68",
    "humidity": "0",
}

POST_PAYLOAD_OPEN_WALKED = {
    "userId": "subhon",
    "doorStatus": "Open",
    "walkThroughStatus": "True",
    "indoorTemp": "68",
    "humidity": "0",
}

POST_PAYLOAD_CLOSED_NOT_WALKED = {
    "userId": "subhon",
    "doorStatus": "Closed",
    "walkThroughStatus": "False",
    "indoorTemp": "68",
    "humidity": "0",
}

POST_PAYLOAD_CLOSED_WALKED = {
    "userId": "subhon",
    "doorStatus": "Closed",
    "walkThroughStatus": "True",
    "indoorTemp": "68",
    "humidity": "0",
}

VSH_URL = "https://www.virtualsmarthome.xyz/url_routine_trigger/activate.php?trigger=110aeef9-cc0b-43af-9ddc-a64dd6a1b79c&token=bcfb8f78-72cd-473f-920e-979a43c66d57&response=html"

dht_device = adafruit_dht.DHT11(board.D17)
last_temp_f = None
last_humidity = None


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


def send_post(payload, label):
    payload = dict(payload)
    temp_f = read_temperature_f()
    humidity = read_humidity()
    if temp_f is not None:
        payload["indoorTemp"] = f"{temp_f:.1f}"
    if humidity is not None:
        payload["humidity"] = f"{humidity:.0f}"
    try:
        resp = requests.post(POST_URL, json=payload, timeout=5)
        resp.raise_for_status()
        print(f"POST ({label}) sent. Response: {resp.status_code} {resp.text}")
        trigger_alexa_routine()
        return True
    except requests.exceptions.RequestException as exc:
        print(f"Failed to send POST ({label}): {exc}")
        return False


def read_temperature_f():
    """Read DHT11 temperature in Fahrenheit; returns last good value on transient errors."""
    global last_temp_f
    try:
        temp_c = dht_device.temperature
        if temp_c is None:
            return last_temp_f
        temp_f = temp_c * (9 / 5) + 32
        last_temp_f = temp_f
        return temp_f
    except RuntimeError as error:
        print(f"DHT read error: {error}")
        return last_temp_f
    except Exception as error:
        dht_device.exit()
        raise


def read_humidity():
    """Read DHT11 humidity; returns last good value on transient errors."""
    global last_humidity
    try:
        humidity = dht_device.humidity
        if humidity is None:
            return last_humidity
        last_humidity = humidity
        return humidity
    except RuntimeError as error:
        print(f"DHT humidity read error: {error}")
        return last_humidity
    except Exception as error:
        dht_device.exit()
        raise


def trigger_alexa_routine():
    """Trigger Alexa routine via Virtual Smart Home URL."""
    try:
        resp = requests.get(VSH_URL, timeout=3)
        resp.raise_for_status()
        print("Triggered Alexa routine successfully.")
    except Exception as exc:
        print(f"Failed to trigger Alexa routine: {exc}")


def main():
    setup_gpio()
    distance_history = deque(maxlen=15)
    stable_door_state = "closed"
    candidate_state = None
    candidate_count = 0
    last_state_change_time = 0.0
    walked_through = False
    walked_through_at = 0.0
    last_post_time = 0.0
    last_payload_signature = None

    try:
        while True:
            distance = measure_distance()
            if distance > 0:
                distance_history.append(distance)

            if len(distance_history) >= 2:
                std_dev = statistics.stdev(distance_history)
            else:
                std_dev = 0.0

            now = time.time()

            new_state = None
            if std_dev >= STD_DEV_HIGH and distance > 0:
                new_state = "open" if distance > DISTANCE_THRESHOLD_CM else "closed"

            if new_state:
                if new_state == candidate_state:
                    candidate_count += 1
                else:
                    candidate_state = new_state
                    candidate_count = 1

                if (
                    candidate_count >= DOOR_STABILITY_COUNT
                    and new_state != stable_door_state
                    and (now - last_state_change_time) >= DOOR_TRANSITION_COOLDOWN_SEC
                ):
                    stable_door_state = new_state
                    last_state_change_time = now
                    print(f"Door state stabilized: {stable_door_state} (distance {distance:.2f} cm, std {std_dev:.2f})")
            else:
                candidate_state = None
                candidate_count = 0

            beam_broken = GPIO.input(BREAKBEAM_PIN) == GPIO.LOW
            if beam_broken:
                if not walked_through:
                    print("Beam broken")
                walked_through = True
                walked_through_at = now
            else:
                if walked_through and (now - walked_through_at) > EVENT_WINDOW_SEC:
                    walked_through = False

            walk_recent = walked_through and (now - walked_through_at) <= EVENT_WINDOW_SEC

            if stable_door_state == "open":
                payload = POST_PAYLOAD_OPEN_WALKED if walk_recent else POST_PAYLOAD_OPEN_NOT_WALKED
                label = "open_walk" if walk_recent else "open"
            else:
                payload = POST_PAYLOAD_CLOSED_WALKED if walk_recent else POST_PAYLOAD_CLOSED_NOT_WALKED
                label = "closed_walk" if walk_recent else "closed"

            payload_signature = (label, payload["doorStatus"], payload["walkThroughStatus"])
            if (now - last_post_time) >= POST_COOLDOWN_SEC and payload_signature != last_payload_signature:
                if send_post(payload, label):
                    last_post_time = now
                    last_payload_signature = payload_signature

            time.sleep(SAMPLE_DELAY_SEC)

    except KeyboardInterrupt:
        print("\nStopping due to keyboard interrupt.")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")


if __name__ == "__main__":
    main()
