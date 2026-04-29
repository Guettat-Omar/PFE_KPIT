#include "window_swich.h"
#include "lin_slave.h"
#include <SoftwareSerial.h>
SoftwareSerial debugSerial(8, 9); // RX, TX
extern volatile uint8_t window_states[4];
volatile bool break_received_flag = false;
volatile bool response_sent_flag = false;

windowState previous_state  [4];
unsigned long last_sample_time ;
const uint8_t ADC_PINS[4] = {A0, A1, A2, A3};
void setup()
{
    debugSerial.begin(9600);
    lin_slave_init();
    last_sample_time = 0;
    for (int i = 0; i < 4; i++)
    {
        previous_state[i] = windowState::UNKNOWN;
    }
    pinMode(13, OUTPUT);
// Blink 3 times at startup = Arduino booted
    for(int i = 0; i < 3; i++) {
        digitalWrite(13, HIGH); delay(300);
        digitalWrite(13, LOW);  delay(300);
    }
}
void loop()
{
    unsigned long now = millis();
    if (now - last_sample_time >= 250) {
        last_sample_time = now;

        // ✅ Sample window states from ADC
        for (int i = 0; i < 4; i++) {
            int val = analogRead(ADC_PINS[i]);
            // Convert ADC reading to window state
            // Adjust thresholds to match your hardware
            if (val < 100) {
                window_states[i] = 0;  // WINDOW_OFF
            } else if (val < 400) {
                window_states[i] = 1;  // WINDOW_DOWN
            } else if (val < 700) {
                window_states[i] = 2;  // WINDOW_UP
            } else {
                window_states[i] = 0;  // default OFF
            }
        }

        // LED debug
        if (break_received_flag) {
            digitalWrite(13, HIGH);
            delay(50);
            digitalWrite(13, LOW);
            break_received_flag = false;
        }

        if (response_sent_flag) {
            for(int i = 0; i < 2; i++) {
                digitalWrite(13, HIGH); delay(50);
                digitalWrite(13, LOW);  delay(50);
            }
            response_sent_flag = false;
        }
    }
}
