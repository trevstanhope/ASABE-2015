/* --- Libraries --- */
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

/* --- Serial / Commands --- */
const int BAUD = 9600;
const int OUTPUT_LENGTH = 256;
const int BEGIN_COMMAND = 'B';
const int ALIGN_COMMAND  = 'A';
const int SEEK_COMMAND  = 'S';
const int GRAB_COMMAND  = 'G';
const int TURN_COMMAND  = 'T';
const int JUMP_COMMAND  = 'J';
const int FINISH_COMMAND  = 'F';
const int REPEAT_COMMAND = 'R';

/* --- Line Following --- */
const int LINE_THRESHOLD = 750;

/* --- I/O Pins --- */
const int CENTER_LINE_PIN = A0;
const int LEFT_LINE_PIN = A1;
const int RIGHT_LINE_PIN = A2;
const int LASER_DIST_PIN = A3;
// A4 - A5 reserved

/* --- PWM Servos --- */
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(); // called this way, it uses the default address 0x40
const int FRONT_LEFT_SERVO = 0;
const int FRONT_RIGHT_SERVO = 1;
const int BACK_LEFT_SERVO = 2;
const int BACK_RIGHT_SERVO = 3;
const int SERVO_MIN = 300;
const int SERVO_OFF = 381; // this is the servo off pulse length
const int SERVO_MAX =  460; // this is the 'maximum' pulse length count (out of 4096)
const int PWM_FREQ = 60; // analog servos run at 60 Hz

/* --- Variables --- */
char command;
int result;

/* --- Buffers --- */
char output[OUTPUT_LENGTH];

/* --- Setup --- */
void setup() {
  Serial.begin(BAUD);
  pinMode(CENTER_LINE_PIN, INPUT);
  pinMode(RIGHT_LINE_PIN, INPUT);
  pinMode(LEFT_LINE_PIN, INPUT);
  pinMode(LASER_DIST_PIN, INPUT); digitalWrite(LASER_DIST_PIN, LOW);
  pwm.begin();
  pwm.setPWMFreq(PWM_FREQ);  // This is the maximum PWM frequency
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF);
}

/* --- Loop --- */
void loop() {
  if (Serial.available() > 0) {
    char val = Serial.read();
    switch (val) {
      case BEGIN_COMMAND:
        command = BEGIN_COMMAND;
        result = begin_run(); break;
      case ALIGN_COMMAND:
        command = ALIGN_COMMAND;
        result = align(); break;
      case SEEK_COMMAND:
        command = SEEK_COMMAND;
        result = seek_plant(); break;
      case GRAB_COMMAND:
        command = GRAB_COMMAND;
        result = grab(); break;
      case TURN_COMMAND:
        command = TURN_COMMAND;
        result = turn(); break;
      case JUMP_COMMAND:
        command = JUMP_COMMAND;
        result = jump(); break;
      case FINISH_COMMAND:
        command = FINISH_COMMAND;
        result = finish_run(); break;
      case REPEAT_COMMAND:
        break;
      default:
        result = 255;
        break;
    }
    sprintf(output, "{'command':'%s','result':%d}", command, result);
    Serial.println(output);
    Serial.flush();
  }
}

/* --- Actions --- */
int begin_run(void) {
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_MAX);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_MIN);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_MAX);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_MIN);
  delay(100);
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF);
  return 0;
}

int seek_plant(void) {
  int center_line = 0;
  int left_line = 0;
  int right_line = 0;
  while ((center_line < LINE_THRESHOLD) && (right_line < LINE_THRESHOLD)  && (left_line < LINE_THRESHOLD)) {
    int dist_ref = analogRead(LASER_DIST_PIN);
    int center_line = analogRead(CENTER_LINE_PIN);
    int left_line = analogRead(LEFT_LINE_PIN);
    int right_line = analogRead(RIGHT_LINE_PIN);
  }  
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

int finish_run(void) {
    return 0;
}
