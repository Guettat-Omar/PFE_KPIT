#include "window_swich.h"

windowState window_swich(int adc_value){
    if (adc_value <B_UP_AUTO)
    {
       return windowState::WINDOW_UP_AUTO;
    }
    else if (adc_value <B_UP)
    {
       return windowState::WINDOW_UP;
    }
    else if (adc_value <B_DOWN_AUTO)
    {
       return windowState::WINDOW_DOWN_AUTO;
    }
    else if (adc_value <B_DOWN)
    {
       return windowState::WINDOW_DOWN;
    }
    else 
    {
       return windowState::WINDOW_OFF;
    }
    
}