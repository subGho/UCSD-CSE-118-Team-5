import RPi.GPIO as GPIO
import time

# Set the GPIO mode
GPIO.setmode(GPIO.BCM) 

# Define the GPIO pin connected to the receiver's signal wire
SENSOR_PIN = 22 

# Set up the GPIO pin as an input with a pull-up resistor
GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

index = 0 

try:
    while True:
        if GPIO.input(SENSOR_PIN) == GPIO.LOW:  # Beam is broken (low logic level)
            print("Beam is broken!", index)
        elif GPIO.input(SENSOR_PIN) == GPIO.HIGH:  # Beam is not broken (high logic level)
            print("Beam is clear!", index)


        index+=1
        time.sleep(0.1) # Small delay to prevent excessive CPU usage

except KeyboardInterrupt:
    GPIO.cleanup() # Clean up GPIO settings on exit
