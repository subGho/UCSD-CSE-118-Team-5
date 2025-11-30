import RPi.GPIO as GPIO
import time
import sys
import statistics

# Define GPIO pin numbers
TRIG_PIN = 23  # Corresponds to your Arduino trigPin
ECHO_PIN = 24 # Corresponds to your Arduino echoPin
THRESHOLD = 20

# Global variables (Python convention uses local variables more often, but we'll mimic the C++ global structure)
# Note: Variables like 'duration' and 'distance' are calculated inside the function
counter = 0
sum_distance = 0.0

changes = [0]*15
idx = 0

def setup():
    """Initializes GPIO and serial communication (equivalent to Arduino setup)."""
    # Use BCM numbering for GPIO pins (physical pins are an alternative)
    GPIO.setmode(GPIO.BCM) 

    # Set up pins
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)

    # Initial output print (equivalent to Serial.println)
    print("The code started working.")

def measure_distance():
    """Performs the distance measurement cycle."""
    # 1. Clear the trigger pin
    GPIO.output(TRIG_PIN, GPIO.LOW)
    time.sleep(0.00002)  # 20 µs just to be safe

    # 2. Send the 10 microsecond pulse
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)  # 10 µs
    GPIO.output(TRIG_PIN, GPIO.LOW)

    # 3. Wait for ECHO to go HIGH (start time)
    timeout = 0.1  # 100 ms timeout
    start_wait = time.time()
    while GPIO.input(ECHO_PIN) == GPIO.LOW:
        if time.time() - start_wait > timeout:
            # print("Timeout waiting for ECHO HIGH")
            return -1  # error / timeout

    pulse_start = time.time()

    # 4. Wait for ECHO to go LOW (end time)
    start_wait = time.time()
    while GPIO.input(ECHO_PIN) == GPIO.HIGH:
        if time.time() - start_wait > timeout:
            # print("Timeout waiting for ECHO LOW")
            return -1

    pulse_end = time.time()

    # 5. Calculate duration and distance
    duration = pulse_end - pulse_start
    distance = (duration * 34300) / 2  # cm

    return distance


def loop():
    """The main loop (equivalent to Arduino loop)."""
    global counter, sum_distance, changes, idx # Declare we're using the global variables

    # Get the distance
    distance = measure_distance()
    changes[idx] = distance
    idx = (idx + 1)%15

    std = statistics.stdev(changes)
        
    print("Standard Deviation: ",std)
    # Process and print the result
    if distance > 0:
        print(f"Distance: {distance:.2f} cm") # Python f-string for formatted output
        
        # Accumulate the distance
        counter += 1
        sum_distance += distance
    else:
        print("Distance: Error/Timeout")

    # The original delay(100)
    time.sleep(0.1) # 100 milliseconds delay

    # The commented-out C++ averaging logic (Optional - Uncomment to use)
    # if counter > 5:
    #     avg_distance = sum_distance / counter
    #     print(f"Average Distance: {avg_distance:.2f} cm")
    #     GPIO.cleanup() # Clean up before exiting
    #     sys.exit(0) # Exit the script

if __name__ == '__main__':
    setup()
    try:
        while True:
            loop()
    except KeyboardInterrupt:
        print("\nProgram stopped by User (Ctrl+C)")
    finally:
        # Final cleanup on exit
        GPIO.cleanup()
        print("GPIO cleaned up.")

