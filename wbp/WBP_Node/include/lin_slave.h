// lin_slave.h
#ifndef LIN_SLAVE_H
#define LIN_SLAVE_H

#include <avr/io.h>
#include <avr/interrupt.h>

#define WBP_FRAME 0x12

enum class LINSlaveState {
    WAIT_BREAK,
    WAIT_SYNC,
    WAIT_PID,
    RESPOND
};

void lin_slave_init();
uint8_t calculate_pid(uint8_t frame_id);
uint8_t calculate_checksum(volatile uint8_t* data, uint8_t pid, uint8_t length);

#endif