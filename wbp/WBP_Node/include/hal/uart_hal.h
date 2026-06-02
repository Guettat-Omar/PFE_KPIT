#pragma once
#include <stdint.h>

void uart_hal_init(uint32_t baud_rate);
void uart_hal_enable_rx_interrupt(void);
void uart_hal_enable_tx_interrupt(void);
void uart_hal_disable_tx_interrupt(void);
void uart_hal_write_byte(uint8_t byte);