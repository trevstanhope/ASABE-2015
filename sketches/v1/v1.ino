/* --- Constants --- */
const int BAUD = 9600;
const float SEEK_PLANT_CMD = 1.1;

/* --- I/O Pins -- */
const int CENTER_LINE_PIN = A0;
const int LEFT_LINE_PIN = A1;
const int RIGHT_LINE_PIN = A2;
const int LASER_DIST_PIN = A3;
// A4 - A5 reserved

void setup() {
  Serial.begin(BAUD);
  pinMode(CENTER_LINE_PIN, INPUT);
  pinMode(RIGHT_LINE_PIN, INPUT);
  pinMode(LEFT_LINE_PIN, INPUT);
  pinMode(LASER_DIST_PIN, INPUT);
}

void loop() {
  if (Serial.available()) {
    float action = Serial.parseFloat();
  }
}
