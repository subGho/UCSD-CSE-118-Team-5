// Pin connected to the break-beam receiver output
const int SENSOR_PIN = 2;

// We'll track the last state so we only print when it changes
int lastState;

void setup() {
  // Initialize Serial Monitor
  Serial.begin(9600);
  // Give serial some time to connect (optional)
  delay(500);

  // Use internal pull-up so the pin reads HIGH when sensor output is "open"
  pinMode(SENSOR_PIN, INPUT_PULLUP);

  // Read initial state
  lastState = digitalRead(SENSOR_PIN);

  Serial.println("Break-beam sensor test started");
}

void loop() {
  int currentState = digitalRead(SENSOR_PIN);

  // Only print when state changes
  if (currentState != lastState) {
    if (currentState == LOW) {
      // Active LOW: beam broken
      Serial.println("Beam is BROKEN");
    } else {
      // HIGH: beam clear
      Serial.println("Beam is CLEAR");
    }

    lastState = currentState;
  }

  // Small delay to avoid spamming, but still pretty responsive
  delay(10);
}
