#pragma once
#include <stdint.h>

void motor_controller_process(uint32_t can_id, const uint8_t* data, uint8_t len);