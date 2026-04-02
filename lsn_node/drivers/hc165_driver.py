"""
74HC165 Driver — Parallel-In Serial-Out Shift Register
Bit-banged GPIO implementation (not hardware SPI)
LSN Node | Raspberry Pi 4B
"""

import RPi.GPIO as GPIO
import time

from hal.gpio_hal import (
    PIN_165_LOAD_PL,
    PIN_165_CLOCK_CP,
    PIN_165_DATA_QH,
    PIN_165_CE
)

PULSE_US = 0.000001


def read_byte():
    GPIO.output(PIN_165_LOAD_PL, GPIO.LOW)
    time.sleep(PULSE_US)
    GPIO.output(PIN_165_LOAD_PL, GPIO.HIGH)
    time.sleep(PULSE_US)
    byte = 0
    for i in range (8):
        bit = GPIO.input(PIN_165_DATA_QH)
        byte = (byte << 1) | bit
        GPIO.output(PIN_165_CLOCK_CP, GPIO.HIGH)
        time.sleep(PULSE_US)
        GPIO.output(PIN_165_CLOCK_CP, GPIO.LOW)
        time.sleep(PULSE_US)
    return byte
def read_all_chips(num_chips=5):
    
    GPIO.output(PIN_165_LOAD_PL, GPIO.LOW)
    time.sleep(PULSE_US)
    GPIO.output(PIN_165_LOAD_PL, GPIO.HIGH)
    time.sleep(PULSE_US)
    
    chips_data = []
    
    for chip in range(num_chips):
        byte = 0
        for i in range(8):
            bit = GPIO.input(PIN_165_DATA_QH)
            byte = (byte << 1) | bit
            GPIO.output(PIN_165_CLOCK_CP, GPIO.HIGH)
            time.sleep(PULSE_US)
            GPIO.output(PIN_165_CLOCK_CP, GPIO.LOW)
            time.sleep(PULSE_US)
        chips_data.append(byte)
    
    return chips_data