"""
74HC165 Driver - Parallel-In Serial-Out Shift Register
Bit-banged GPIO implementation (not hardware SPI)
LSN Node | Raspberry Pi 4B

LAYER: Driver Layer (Interfaces App Layer with HAL Layer)
"""

import RPi.GPIO as GPIO
import time
import logging


from hal.gpio_hal import (
    PIN_165_LOAD_PL,
    PIN_165_CLOCK_CP,
    PIN_165_DATA_QH,
    PIN_165_CE
)
from config import PULSE_US

logger = logging.getLogger(__name__)


def read_byte():
    """
    Reads a single byte (8 bits) from the 74HC165 shift register.
    :return: An integer representing the read byte.
    """
    logger.debug("Reading single byte from 74HC165.")
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
    """
    Reads data from multiple cascaded 74HC165 shift registers.
    :param num_chips: The number of daisy-chained shift registers.
    :return: A list of bytes, one for each chip.
    """
    logger.debug(f"Reading data from {num_chips} cascaded 74HC165 chips.")
    
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
