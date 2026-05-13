#pragma once
#include <Arduino.h>

enum class windowState {
    WINDOW_OFF, 
    WINDOW_DOWN, 
    WINDOW_UP,
    WINDOW_UP_AUTO,
    WINDOW_DOWN_AUTO,
    UNKNOWN
};

const uint16_t B_UP_AUTO   = 282;
const uint16_t B_UP        = 400;
const uint16_t B_DOWN_AUTO = 452;
const uint16_t B_DOWN      = 542;


windowState window_swich(uint16_t adc_value);

