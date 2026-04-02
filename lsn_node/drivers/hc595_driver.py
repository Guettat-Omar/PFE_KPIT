"""
74HC595 Driver - Serial-In Parallel-Out Shift Register
Bit-banged GPIO implementation to drive LED outputs.
LSN Node | Raspberry Pi 4B

LAYER: Driver Layer (Interfaces App Layer with HAL Layer)
"""

import RPi.GPIO as GPIO
import time
import logging

from hal.gpio_hal import (
    PIN_595_DATA_SER,
    PIN_595_SHIFT_SRCLK,
    PIN_595_LATCH_RCLK,
    PIN_595_RESET
)
from config import PULSE_US

logger = logging.getLogger(__name__)


def _shift_byte(byte):
    """
    Internal helper to shift a single byte into the 74HC595 (without latching).
    Shifts MSB first.
    """
    for i in range(7, -1, -1):
        bit = (byte >> i) & 1
        GPIO.output(PIN_595_DATA_SER, GPIO.HIGH if bit else GPIO.LOW)
        GPIO.output(PIN_595_SHIFT_SRCLK, GPIO.HIGH)
        time.sleep(PULSE_US)
        GPIO.output(PIN_595_SHIFT_SRCLK, GPIO.LOW)
        time.sleep(PULSE_US)

def _latch():
    """
    Internal helper to pulse the RCLK pin, transferring data from the 
    shift register to the storage register (updating the actual output pins).
    """
    GPIO.output(PIN_595_LATCH_RCLK, GPIO.HIGH)
    time.sleep(PULSE_US)
    GPIO.output(PIN_595_LATCH_RCLK, GPIO.LOW)
    time.sleep(PULSE_US)

def write_byte(byte):
    """
    Shifts and latches a single byte to the 74HC595.
    :param byte: The byte to write.
    """
    logger.debug(f"Writing single byte to 74HC595: {hex(byte)}")
    _shift_byte(byte)
    _latch()

def reset():
    """
    Pulses the Master Reset (MR) pin LOW to clear the shift register.
    """
    logger.info("Resetting 74HC595 shift registers...")
    GPIO.output(PIN_595_RESET, GPIO.LOW)
    time.sleep(PULSE_US)
    GPIO.output(PIN_595_RESET, GPIO.HIGH)
    time.sleep(PULSE_US)

def write_all_chips(sended_data):
    """
    Writes a list/tuple of bytes to multiple cascaded 74HC595 shift registers.
    :param sended_data: Iterable of bytes to write.
    """
    logger.debug(f"Writing block of {len(sended_data)} bytes to cascaded 595s.")
    try:
        # The last chip in the chain receives the first pushed byte, so we reverse it.
        for byte in reversed(sended_data):
            _shift_byte(byte)
        _latch()
    except Exception as e:
        logger.error(f"Failed to write to 74HC595 chain: {e}")
        raise

def shutdown_leds():
    """
    Convenience function to clear all output LEDs by writing 0x00.
    """
    logger.info("Shutting down all LEDs on 595 cascade.")
    write_all_chips([0x00] * 5)