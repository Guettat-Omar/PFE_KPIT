#include "window_swich.h"

windowState previous_state = windowState::UNKNOWN;

void setup()
{
    Serial.begin(9600);
}
void loop()
{
    int current_adc_value = analogRead(A0);

    // Uncomment this line to debug the raw resistance values if the states aren't changing:
    
    Serial.println(current_adc_value);
    delay(250);

    windowState current_state = window_swich(current_adc_value);
    if (current_state != previous_state)
    {
        Serial.print("window1_state: ");
        Serial.println(static_cast<int>(current_state));
        previous_state = current_state;
    }
}