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

const uint16_t ADC_UP_MAX = 260;
const uint16_t ADC_UP_MIN = 180;
const uint16_t ADC_DOWN_MAX = 400;
const uint16_t ADC_DOWN_MIN = 300;
const uint16_t ADC_UP_AUTO_MAX = 100;
const uint16_t ADC_UP_AUTO_MIN = 40;
const uint16_t ADC_DOWN_AUTO_MAX = 290;
const uint16_t ADC_DOWN_AUTO_MIN = 250;
const uint16_t ADC_OFF_MIN = 410;
const uint16_t ADC_OFF_MAX = 500;


windowState window_swich(int adc_value);

