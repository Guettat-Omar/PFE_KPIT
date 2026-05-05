#include "motor_driver.h"
#include <Arduino.h>
#include "config.h"
void set_motor(int pin_en, int pin_in1, int pin_in2, uint8_t command){
    if (command == CMD_UP) {
        digitalWrite(pin_in1, HIGH);
        digitalWrite(pin_in2, LOW);
        analogWrite(pin_en, 255);
    } else if (command == CMD_DOWN) {
        digitalWrite(pin_in1, LOW);
        digitalWrite(pin_in2, HIGH);
        analogWrite(pin_en, 255);
    } else { // CMD_STOP
        digitalWrite(pin_in1, LOW);
        digitalWrite(pin_in2, LOW);
        analogWrite(pin_en, 0);
    }
}
void motor_driver_init() {
    pinMode(ENA_WA, OUTPUT);
    pinMode(IN1_WA, OUTPUT);
    pinMode(IN2_WA, OUTPUT);
    
    pinMode(ENB_WB, OUTPUT);
    pinMode(IN3_WB, OUTPUT);
    pinMode(IN4_WB, OUTPUT);
    
    pinMode(ENA_PA, OUTPUT);
    pinMode(INP1_PA, OUTPUT);
    pinMode(INP2_PA, OUTPUT);
    
    pinMode(ENB_PB, OUTPUT);
    pinMode(INP1_PB, OUTPUT);
    pinMode(INP2_PB, OUTPUT);
}
void motorWA_command(uint8_t command) {
    set_motor(ENA_WA, IN1_WA, IN2_WA, command);
}
void motorWB_command(uint8_t command) {
    set_motor(ENB_WB, IN3_WB, IN4_WB, command);
}
void motorPA_command(uint8_t command) {
    set_motor(ENA_PA, INP1_PA, INP2_PA, command);
}
void motorPB_command(uint8_t command) {
    set_motor(ENB_PB, INP1_PB, INP2_PB, command);
}
void stop_all_motors() {
    motorWA_command(CMD_STOP);
    motorWB_command(CMD_STOP);
    motorPA_command(CMD_STOP);
    motorPB_command(CMD_STOP);
}