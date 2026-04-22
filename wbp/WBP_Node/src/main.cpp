#include "window_swich.h"

windowState previous_state  [4];
unsigned long last_sample_time ;
const uint8_t ADC_PINS[4] = {A0, A1, A2, A3};
void setup()
{
    Serial.begin(9600);
    last_sample_time = 0;
    for (int i = 0; i < 4; i++)
    {
        previous_state[i] = windowState::UNKNOWN;
    }
    
}
void loop()
{
    unsigned long now = millis();
    int current_adc_value[4];
    windowState current_state[4];
    if (now - last_sample_time >= 250) {
            last_sample_time = now;
            for (int i = 0; i < 4; i++)
            {
                current_adc_value[i] = analogRead(ADC_PINS[i]);
                current_state[i] = window_swich(current_adc_value[i]);
                    if (current_state[i] != previous_state[i])
    {
        Serial.print("window");
        Serial.print(i + 1);
        Serial.print("_state: ");
        Serial.println(static_cast<int>(current_state[i]));
        previous_state[i] = current_state[i];
    }
    }

}
}