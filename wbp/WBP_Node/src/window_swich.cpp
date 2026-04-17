#include "window_swich.h"

windowState window_swich(int adc_value){
    if (adc_value >ADC_DOWN_MIN && adc_value <ADC_DOWN_MAX)
    {
       return windowState::WINDOW_DOWN;
    }
    else if (adc_value >ADC_UP_MIN && adc_value <ADC_UP_MAX)
    {
       return windowState::WINDOW_UP;
    }
    else if (adc_value >ADC_UP_AUTO_MIN && adc_value <ADC_UP_AUTO_MAX)
    {
       return windowState::WINDOW_UP_AUTO;
    }
    else if (adc_value >ADC_DOWN_AUTO_MIN && adc_value <ADC_DOWN_AUTO_MAX)
    {
       return windowState::WINDOW_DOWN_AUTO;
    }
    else if (adc_value > ADC_OFF_MIN && adc_value < ADC_OFF_MAX)
    {
       return windowState::WINDOW_OFF;
    }
    else
    {
       return windowState::UNKNOWN;
    }
    
}