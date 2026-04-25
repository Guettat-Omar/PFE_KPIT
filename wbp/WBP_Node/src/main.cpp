#include "window_swich.h"
#include "lin_slave.h"
#include <SoftwareSerial.h>
SoftwareSerial debugSerial(8, 9); // RX, TX
extern volatile uint8_t window_states[4];

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
    
}
void loop()
{
    unsigned long now = millis();
    if (now - last_sample_time >= 250) {
            last_sample_time = now;
            int current_adc_value[4];
            windowState current_state[4];
            for (int i = 0; i < 4; i++)
            {
                current_adc_value[i] = analogRead(ADC_PINS[i]);
                current_state[i] = window_swich(current_adc_value[i]);
                window_states[i] = static_cast<uint8_t>(current_state[i]);
            }
            debugSerial.print("W0:"); debugSerial.print(window_states[0]);
            debugSerial.print(" W1:"); debugSerial.print(window_states[1]);
            debugSerial.print(" W2:"); debugSerial.print(window_states[2]);
            debugSerial.print(" W3:"); debugSerial.println(window_states[3]);
        }
    }