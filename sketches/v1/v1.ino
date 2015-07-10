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
const int FINISH_COMMAND  = 'E';

/* --- Line Following --- */
const int LINE_THRESHOLD = 800;

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
const int FRONT_LEFT_MIN = 300;
const int FRONT_LEFT_OFF = 381; // this is the servo off pulse length
const int FRONT_LEFT_MAX =  460; // this is the 'maximum' pulse length count (out of 4096)
const int FRONT_RIGHT_MIN = 300;
const int FRONT_RIGHT_OFF = 378; // this is the servo off pulse length
const int FRONT_RIGHT_MAX =  460; // this is the 'maximum' pulse length count (out of 4096)
const int BACK_LEFT_MIN = 300;
const int BACK_LEFT_OFF = 378; // this is the servo off pulse length
const int BACK_LEFT_MAX =  460; // this is the 'maximum' pulse length count (out of 4096)
const int BACK_RIGHT_MIN = 300;
const int BACK_RIGHT_OFF = 378; // this is the servo off pulse length
const int BACK_RIGHT_MAX =  460; // this is the 'maximum' pulse length count (out of 4096)
const int PWM_FREQ = 60; // analog servos run at 60 Hz

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
  pwm.setPWM(FRONT_LEFT_SERVO, 0, FRONT_LEFT_OFF);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, FRONT_RIGHT_OFF);
  pwm.setPWM(BACK_LEFT_SERVO, 0, BACK_LEFT_OFF);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, BACK_RIGHT_OFF);
}

/* --- Loop --- */
void loop() {
  if (Serial.available() > 0) {
    char action = Serial.read();
    switch (action) {
      case BEGIN_COMMAND:
        begin_run(); break;
      case ALIGN_COMMAND:
        align(); break;
      case SEEK_COMMAND:
        seek_plant(); break;
      case GRAB_COMMAND:
        grab(); break;
      case TURN_COMMAND:
        turn(); break;
      case JUMP_COMMAND:
        jump(); break;
      case FINISH_COMMAND:
        finish_run(); break;
      default:
        break;
    }
    //sprintf(output, "{'action':%s}", action);
    //Serial.println(output);
    //Serial.flush();
  }
}

/* --- Actions --- */
int begin_run(void) {
  pwm.setPWM(FRONT_LEFT_SERVO, 0, FRONT_LEFT_MAX);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, FRONT_RIGHT_MIN);
  pwm.setPWM(BACK_LEFT_SERVO, 0, BACK_LEFT_MAX);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, BACK_RIGHT_MIN);
  delay(100);
  pwm.setPWM(FRONT_LEFT_SERVO, 0, FRONT_LEFT_OFF);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, FRONT_RIGHT_OFF);
  pwm.setPWM(BACK_LEFT_SERVO, 0, BACK_LEFT_OFF);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, BACK_RIGHT_OFF);
  return 0;
}

int seek_plant(void) {
  int center_line = 0;
  int left_line = 0;
  int right_line = 0;
  while ((center_line < LINE_THRESHOLD) && (right_line < LINE_THRESHOLD)  && (left_line < LINE_THRESHOLD)) {
    int center_line = analogRead(CENTER_LINE_PIN);
    int left_line = analogRead(LEFT_LINE_PIN);
    int right_line = analogRead(RIGHT_LINE_PIN);
    Serial.print(left_line); Serial.print(' ');
    Serial.print(center_line); Serial.print(' ');
    Serial.print(right_line); Serial.println(' ');

  }

  
  int dist_ref = analogRead(LASER_DIST_PIN);
  
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
