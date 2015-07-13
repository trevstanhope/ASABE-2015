/* --- Libraries --- */
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

/* --- Time Constants --- */
const int WAIT_INTERVAL = 1000;
const int BEGIN_INTERVAL = 2000;
const int TURN45_INTERVAL = 1000;
const int TURN90_INTERVAL = 1000;
const int GRAB_INTERVAL = 1000;
const int FINISH_INTERVAL = 3000; // interval to move fully into finishing square

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
const int WAIT_COMMAND = 'W';
const int REPEAT_COMMAND = 'R';
const int UNKNOWN_COMMAND = '?';

/* --- Line Following --- */
const int LINE_THRESHOLD = 750;

/* --- I/O Pins --- */
const int CENTER_LINE_PIN = A0;
const int LEFT_LINE_PIN = A1;
const int RIGHT_LINE_PIN = A2;
const int DIST_SENSOR_PIN = A3;
// A4 - A5 reserved

/* --- PWM Servos --- */
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(); // called this way, it uses the default address 0x40
const int FRONT_LEFT_SERVO = 0;
const int FRONT_RIGHT_SERVO = 1;
const int BACK_LEFT_SERVO = 2;
const int BACK_RIGHT_SERVO = 3;
const int ARM_SERVO = 4;
const int MICROSERVO_MIN = 150;
const int MICROSERVO_ZERO = 400; // this is the servo off pulse length
const int MICROSERVO_MAX =  600; // this is the 'maximum' pulse length count (out of 4096)
const int SERVO_MIN = 300;
const int SERVO_OFF = 380; // this is the servo off pulse length
const int SERVO_MAX =  460; // this is the 'maximum' pulse length count (out of 4096)
const int PWM_FREQ = 60; // analog servos run at 60 Hz
const int SERVO_SLOW = 10;

/* --- Variables --- */
char command;
int result;
int center_line = 0;
int left_line = 0;
int right_line = 0;
int at_plant = 0; // 0: not at plant, 1-5: plant number
int at_end = 0; // 0: not at end, 1: 1st end of row, 2: 2nd end of row
int pass = 0; // 0: not specified, 1: right-to-left, -1: left-to-rightd

/* --- Buffers --- */
char output[OUTPUT_LENGTH];

/* --- Setup --- */
void setup() {
  Serial.begin(BAUD);
  pinMode(CENTER_LINE_PIN, INPUT);
  pinMode(RIGHT_LINE_PIN, INPUT);
  pinMode(LEFT_LINE_PIN, INPUT);
  pinMode(DIST_SENSOR_PIN, INPUT);
  pwm.begin();
  pwm.setPWMFreq(PWM_FREQ);  // This is the ideal PWM frequency for servos
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(ARM_SERVO, 0, MICROSERVO_MAX); // it's fixed rotation, not continous

}

/* --- Loop --- */
void loop() {
  if (Serial.available() > 0) {
    char val = Serial.read();
    switch (val) {
      case BEGIN_COMMAND:
        command = BEGIN_COMMAND;
        result = begin_run();
        break;
      case ALIGN_COMMAND:
        command = ALIGN_COMMAND;
        result = align();
        break;
      case SEEK_COMMAND:
        command = SEEK_COMMAND;
        result = seek_plant();
        break;
      case GRAB_COMMAND:
        command = GRAB_COMMAND;
        result = grab();
        break;
      case TURN_COMMAND:
        command = TURN_COMMAND;
        result = turn();
        break;
      case JUMP_COMMAND:
        command = JUMP_COMMAND;
        result = jump();
        break;
      case FINISH_COMMAND:
        command = FINISH_COMMAND;
        result = finish_run();
        break;
      case REPEAT_COMMAND:
        break;
      case WAIT_COMMAND:
        command = WAIT_COMMAND;
        result = wait();
        break;
      default:
        result = 255;
        command = UNKNOWN_COMMAND;
        break;
    }
    sprintf(output, "{'command':'%c','result':%d,'at_plant':%d,'at_end':%d,'pass':%d}", command, result, at_plant, at_end, pass);
    Serial.println(output);
    Serial.flush();
  }
}

/* --- Actions --- */
int begin_run(void) {
  // Move Arm
  pwm.setPWM(ARM_SERVO, 0, MICROSERVO_MIN);
  // Get past black square
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF - SERVO_SLOW);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF - SERVO_SLOW);
  delay(BEGIN_INTERVAL);
  // Run until line found
  while (center_line < LINE_THRESHOLD) {
      update_lines();
      pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
      pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF - SERVO_SLOW);
      pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
      pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF - SERVO_SLOW);
  }
  // Stop
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF);
  pass = 1;
  return 0;
}

int seek_plant(void) {
  at_end = 0;
  while ((center_line < LINE_THRESHOLD) && (right_line < LINE_THRESHOLD)  && (left_line < LINE_THRESHOLD)) {
    update_lines();
  }
  if (pass == 1) {
    at_end = 2;
  }
  else if (pass == -1) {
    at_end = 1;
  }
  return 0;
}

int jump(void) {
  // Turn Left 45 degs
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  delay(TURN45_INTERVAL);
  // Turn Left 90 degs
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  delay(TURN90_INTERVAL);
  // Run until line
  while (center_line < LINE_THRESHOLD) {
      update_lines();
      pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
      pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF - SERVO_SLOW);
      pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
      pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF - SERVO_SLOW);
  }
  // Stop
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF);
  at_end = 0;
  pass = 1;
  return 0;
}

int turn(void) {
  // Turn 45 degrees
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  delay(TURN45_INTERVAL);
  // Turn until line
  while (center_line < LINE_THRESHOLD) {
    update_lines();
    pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
    pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
    pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
    pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF + SERVO_SLOW);
  }
  // Stop
  pwm.setPWM(FRONT_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(FRONT_RIGHT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_LEFT_SERVO, 0, SERVO_OFF);
  pwm.setPWM(BACK_RIGHT_SERVO, 0, SERVO_OFF);
  if (pass == 1) {
    pass = -1;
  }
  at_end = 0;
  return 0;
}

int grab(void) {
    // Retract arm fully
    pwm.setPWM(ARM_SERVO, 0, MICROSERVO_MIN);
    delay(GRAB_INTERVAL);
    // Grab block
    pwm.setPWM(ARM_SERVO, 0, MICROSERVO_MAX);
    delay(GRAB_INTERVAL);
    // Return arm to initial position
    pwm.setPWM(ARM_SERVO, 0, MICROSERVO_MIN);
    delay(GRAB_INTERVAL);
    return 0;
}

int align(void) {
  if (pass == 0) {
    return 1;
  }
  else if (pass == 1) {
    at_end = 1;
  }
  else if (pass == -1) {
    at_end = 2;
  }
  return 0;
}

int finish_run(void) {
    // Move Forward
    // Turn Right 90 degrees
    // Go until finish square
    // Step into square
    return 0;
}

int wait(void) {
  delay(WAIT_INTERVAL);
  return 0;
}

void update_lines(void) {
  center_line = analogRead(CENTER_LINE_PIN);
  left_line = analogRead(LEFT_LINE_PIN);
  right_line = analogRead(RIGHT_LINE_PIN);
}

void update_plant(void) {
  int dist = analogRead(DIST_SENSOR_PIN);
  at_plant = 0;
}
