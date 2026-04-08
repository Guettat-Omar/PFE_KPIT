"""
GPIO HAL � Hardware Abstraction Layer
LSN Node | Raspberry Pi 4B
Defines and initializes all GPIO pins used in the project.
"""

import RPi.GPIO as GPIO
import logging
logger = logging.getLogger(__name__)

from config import (
    PIN_165_LOAD_PL, PIN_165_CLOCK_CP, PIN_165_DATA_QH, PIN_165_CE,
    PIN_595_DATA_SER, PIN_595_SHIFT_SRCLK, PIN_595_LATCH_RCLK, PIN_595_RESET,
    MCP2515_INT)
# SPI0: SCLK=GPIO11, MISO=GPIO9, MOSI=GPIO10, CS=GPIO8 (handled by kernel)

# --- LIN Bus (UART0) ----------------------------------------------------------
# TX=GPIO14, RX=GPIO15 (handled by pyserial, not GPIO)

def init_gpio():
    GPIO.setmode(GPIO.BCM)
    #74hc165 pin intialization
    GPIO.setup(PIN_165_LOAD_PL,GPIO.OUT,initial=GPIO.HIGH)
    GPIO.setup(PIN_165_CLOCK_CP,GPIO.OUT)
    GPIO.setup(PIN_165_DATA_QH,GPIO.IN)
    GPIO.setup(PIN_165_CE,GPIO.OUT,initial=GPIO.LOW)
    #74hc595 pin intialization
    GPIO.setup(PIN_595_LATCH_RCLK,GPIO.OUT)
    GPIO.setup(PIN_595_DATA_SER,GPIO.OUT)
    GPIO.setup(PIN_595_SHIFT_SRCLK,GPIO.OUT)
    GPIO.setup(PIN_595_RESET,GPIO.OUT,initial=GPIO.HIGH)
    #mc2515 pin intialization
    GPIO.setup(MCP2515_INT,GPIO.IN)
    logger.info("[GPIO HAL] All pins initialized.")
  
def cleanup_gpio():
    GPIO.cleanup()
    logger.info("[GPIO HAL] GPIO cleaned up.")