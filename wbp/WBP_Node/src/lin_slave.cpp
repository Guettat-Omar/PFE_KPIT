#include "lin_slave.h"
volatile uint8_t window_states[4];
extern volatile bool break_received_flag;
extern volatile bool response_sent_flag;
volatile uint8_t tx_index = 0;
volatile uint8_t tx_length = 0;
volatile uint8_t tx_buffer[5];

void lin_slave_init() {
    UBRR0H = 0;
    UBRR0L = 51;
    // Enable receiver and transmitter
    UCSR0B = (1 << RXEN0) | (1 << TXEN0) | (1 << RXCIE0);
    // 8 data bits, 1 stop bit, no parity
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);
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
            break_received_flag = true;
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
            // Send response immediately — no separate RESPOND state needed
            uint8_t pid = calculate_pid(WBP_FRAME);
            for (int i = 0; i < 4; i++) {
                tx_buffer[i]= window_states[i];      
            }
            tx_buffer[4] = calculate_checksum(tx_buffer, pid, 4);
            tx_index = 0;
            UCSR0B |= (1 << UDRIE0);
            tx_length = 5;
        state = LINSlaveState::WAIT_BREAK;
        break; 

    default:
        break;
    }
}}
 ISR(USART_UDRE_vect){
    if (tx_index<tx_length)
    {
        UDR0 =tx_buffer[tx_index];
        tx_index++;
    }
    else
    {
        UCSR0B &= ~(1 << UDRIE0);
        response_sent_flag = true;
    }
    
}
uint8_t calculate_pid(uint8_t frame_id) {
    uint8_t p0 = (frame_id & 0x01) ^ ((frame_id >> 1) & 0x01) ^ ((frame_id >> 2) & 0x01) ^ ((frame_id >> 4) & 0x01);
    uint8_t p1 = !(((frame_id >> 1) & 0x01) ^ ((frame_id >> 3) & 0x01) ^ ((frame_id >> 4) & 0x01) ^ ((frame_id >> 5) & 0x01)) & 0x01;
    return (p1 << 7) | (p0 << 6) | frame_id;
}
uint8_t calculate_checksum(volatile uint8_t* data, uint8_t pid, uint8_t length) {
    uint16_t sum = pid;
    for (uint8_t i = 0; i < length; i++) {
        sum += data[i];
        if (sum > 255) {
            sum -= 255;
        }
    }
    return ~sum & 0xFF;
}