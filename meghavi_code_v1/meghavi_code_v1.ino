#define PIR_PIN 2      // PIR sensor connected to digital pin 2
#define TRIG_PIN 9
#define ECHO_PIN 10

int var = 0;

void setup() {
    Serial.begin(9600);   // Start Serial communication
    pinMode(PIR_PIN, INPUT);
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
}

void loop() {
    // Measure distance
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    long duration = pulseIn(ECHO_PIN, HIGH);
    float distance = (duration*.0343)/2;

    // Check for motion and distance < 2 meters
    if (digitalRead(PIR_PIN) == HIGH && distance<200) {
        var++;
        Serial.print("Motion_Detected : ");
        Serial.print(var);
        Serial.print(" | Distance: ");
        Serial.print(distance);
        Serial.println(" cm");
        delay(2000);  // Debounce delay
    }
}
