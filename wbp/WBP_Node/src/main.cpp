#include "window_swich.h"
#include "lin_slave.h"
extern volatile uint8_t window_states[4];

windowState previous_state  [4];
int current_adc_value[4];
windowState current_state[4];
unsigned long last_sample_time ;
const uint8_t ADC_PINS[4] = {A0, A1, A2, A3};
void setup()
{
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
            for (int i = 0; i < 4; i++)
            {
                current_adc_value[i] = analogRead(ADC_PINS[i]);
                current_state[i] = window_swich(current_adc_value[i]);
                uint8_t err = (current_state[i] == windowState::UNKNOWN) ? 1 : 0;
                uint8_t state = (current_state[i] == windowState::UNKNOWN) ? 0 : static_cast<uint8_t>(current_state[i]);
                window_states[i] = state | (err << 3);
            }
        }
    }