/* --- Libraries --- */
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

/* --- Constants --- */
const int BAUD = 9600;
const char BEGIN_COMMAND = 'B';
const char ALIGN_COMMAND  = 'A';
const char SEEK_COMMAND  = 'S';
const char GRAB_COMMAND  = 'G';
const char TURN_COMMAND  = 'T';
const char JUMP_COMMAND  = 'J';
const char END_COMMAND  = 'E';
const int SERVO_MIN = 150; // this is the 'minimum' pulse length count (out of 4096)
const int SERVO_MAX =  600; // this is the 'maximum' pulse length count (out of 4096)
const int PWM_FREQ = 60; // analog servos run at 60 Hz
const int LINE_THRESHOLD = 800;

/* --- I/O Pins -- */
const int CENTER_LINE_PIN = A0;
const int LEFT_LINE_PIN = A1;
const int RIGHT_LINE_PIN = A2;
const int LASER_DIST_PIN = A3;
// A4 - A5 reserved

/* --- PWM --- */
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(); // called this way, it uses the default address 0x40
const int FRONT_LEFT_SERVO = 0;
const int FRONT_RIGHT_SERVO = 1;
const int BACK_LEFT_SERVO = 2;
const int BACK_RIGHT_SERVO = 3;

void setup() {
  Serial.begin(BAUD);
  pinMode(CENTER_LINE_PIN, INPUT);
  pinMode(RIGHT_LINE_PIN, INPUT);
  pinMode(LEFT_LINE_PIN, INPUT);
  pinMode(LASER_DIST_PIN, INPUT); digitalWrite(LASER_DIST_PIN, LOW);
  pwm.begin();
  pwm.setPWMFreq(PWM_FREQ);  // This is the maximum PWM frequency
}

void loop() {
  //if (Serial.available()) {
    //float action = Serial.parseFloat();
  //}
//  for (uint16_t i = 0; i < 4096; i++) { 
//    pwm.setPWM(FRONT_LEFT_SERVO, 0, i);
//  }
  int center_ref = analogRead(CENTER_LINE_PIN);
  int left_ref = analogRead(LEFT_LINE_PIN);
  int right_ref = analogRead(RIGHT_LINE_PIN);
  int dist_ref = analogRead(LASER_DIST_PIN);
 
  Serial.println(dist_ref);
}
/* --- Actions --- */
int begin(void) {
  return 0;
}

int seek(void) {
  return 0;
}

int jump(void) {
  return 0;
}

int turn(void) {
  return 0;
}

int grab(void) {
    return 0;
}

int align(void) {
  return 0;
}

int end(void) {
    return 0;
}
