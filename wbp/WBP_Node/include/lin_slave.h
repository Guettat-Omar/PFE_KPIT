#pragma once
#include <Arduino.h>
const uint8_t WBP_FRAME = 0x12;
enum class LINSlaveState {
    WAIT_BREAK,
    WAIT_SYNC,
    WAIT_PID,
    RESPOND
};
 void lin_slave_init();
 uint8_t calculate_pid(uint8_t frame_id);
 void lin_slave_process (uint8_t* data, uint8_t length);
