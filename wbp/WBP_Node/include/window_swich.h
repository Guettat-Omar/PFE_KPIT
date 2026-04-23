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

const uint16_t B_UP_AUTO  = 145;
const uint16_t B_UP       = 245;
const uint16_t B_DOWN_AUTO = 310;
const uint16_t B_DOWN     = 402;


windowState window_swich(int adc_value);

