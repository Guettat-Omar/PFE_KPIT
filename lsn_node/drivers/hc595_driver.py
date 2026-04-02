import RPi.GPIO as GPIO
import time
from hal.gpio_hal import (
    PIN_595_DATA_SER,
    PIN_595_SHIFT_SRCLK,
    PIN_595_LATCH_RCLK,
    PIN_595_RESET
)

PULSE_US = 0.000001  # 1 microsecond

def _shift_byte(byte):
    for i in range(7, -1, -1):
        bit = (byte >> i) & 1
        GPIO.output(PIN_595_DATA_SER, GPIO.HIGH if bit else GPIO.LOW)
        GPIO.output(PIN_595_SHIFT_SRCLK, GPIO.HIGH)
        time.sleep(PULSE_US)
        GPIO.output(PIN_595_SHIFT_SRCLK, GPIO.LOW)
        time.sleep(PULSE_US)

def _latch():
    GPIO.output(PIN_595_LATCH_RCLK, GPIO.HIGH)
    time.sleep(PULSE_US)
    GPIO.output(PIN_595_LATCH_RCLK, GPIO.LOW)
    time.sleep(PULSE_US)

def write_byte(byte):
    _shift_byte(byte)
    _latch()

def reset():
    GPIO.output(PIN_595_RESET, GPIO.LOW)
    time.sleep(PULSE_US)
    GPIO.output(PIN_595_RESET, GPIO.HIGH)
    time.sleep(PULSE_US)

def write_all_chips(sended_data):
    for byte in reversed(sended_data):
        _shift_byte(byte)
    _latch()

def shutdown_leds():
    write_all_chips([0x00] * 5)