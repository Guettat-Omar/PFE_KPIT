#pragma once
#include <Arduino.h>

enum class windowState
{
    WINDOW_OFF,
    WINDOW_DOWN,
    WINDOW_UP,
    WINDOW_UP_AUTO,
    WINDOW_DOWN_AUTO,
    UNKNOWN
};

const uint16_t B_UP_AUTO   = 30;   // midpoint between 15 and 46
const uint16_t B_UP        = 58;   // midpoint between 46 and 71
const uint16_t B_DOWN_AUTO = 89;   // midpoint between 71 and 107
const uint16_t B_DOWN      = 279;

windowState window_switch(uint16_t adc_value);
