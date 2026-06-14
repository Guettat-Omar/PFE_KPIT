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

const uint16_t B_UP_AUTO   = 23;
const uint16_t B_UP        = 52;
const uint16_t B_DOWN_AUTO = 81;
const uint16_t B_DOWN      = 273;

windowState window_switch(uint16_t adc_value);
