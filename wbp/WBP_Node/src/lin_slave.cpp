#include "lin_slave.h"
volatile uint8_t window_states[4];

void lin_slave_init() {
    Serial.begin(19200); 
    UCSR0B |= (1 << RXCIE0); 
    sei();
}

ISR (USART_RX_vect){
    static volatile LINSlaveState state = LINSlaveState::WAIT_BREAK ;
    uint8_t flag = UCSR0A;
    uint8_t received_byte = UDR0;
    switch (state)
    {
    case LINSlaveState::WAIT_BREAK:
        if (flag & (1<<FE0))
        {
            state = LINSlaveState::WAIT_SYNC;
        }
        else
        {
            state = LINSlaveState::WAIT_BREAK;
        }
        break;
    case LINSlaveState::WAIT_SYNC:
        if (received_byte == 0x55) {
            state = LINSlaveState::WAIT_PID;
        } else {
            state = LINSlaveState::WAIT_BREAK;
        }
        break;
    case LINSlaveState::WAIT_PID:
        if (received_byte == calculate_pid(WBP_FRAME)) {
            state = LINSlaveState::RESPOND;
        } else {
            state = LINSlaveState::WAIT_BREAK;
        }
        break;  
    case LINSlaveState::RESPOND:
        for (int i = 0; i < 4; i++) {
            while (!(UCSR0A & (1 << UDRE0)));
            UDR0 = window_states[i];
        }
        while (!(UCSR0A & (1 << UDRE0)));
        UDR0 = calculate_checksum(window_states, 4);

        state = LINSlaveState::WAIT_BREAK;
        break;
    default:
        break;
    }
}
uint8_t calculate_pid(uint8_t frame_id) {
    uint8_t p0 = (frame_id & 0x01) ^ ((frame_id >> 1) & 0x01) ^ ((frame_id >> 2) & 0x01) ^ ((frame_id >> 4) & 0x01);
    uint8_t p1 = !(((frame_id >> 1) & 0x01) ^ ((frame_id >> 3) & 0x01) ^ ((frame_id >> 4) & 0x01) ^ ((frame_id >> 5) & 0x01)) & 0x01;
    return (p1 << 7) | (p0 << 6) | frame_id;
}
uint8_t calculate_checksum(volatile uint8_t* data, uint8_t length) {
    uint8_t sum = 0;
    for (uint8_t i = 0; i < length; i++) {
        sum += data[i];
        if (sum > 255) {
            sum -= 255;
        }
    }
    return ~sum & 0xFF;
}