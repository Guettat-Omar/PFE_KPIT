#ifndef MOTOR_DRIVER_H
#define MOTOR_DRIVER_H
#include <Arduino.h>
void set_motor(int pin_en, int pin_in1, int pin_in2, uint8_t command);
void motor_driver_init();
void motorWA_command(uint8_t command);
void motorWB_command(uint8_t command);
void motorPA_command(uint8_t command);
void motorPB_command(uint8_t command);
void stop_all_motors();
#endif