"""
GPIO HAL — Hardware Abstraction Layer
LSN Node | Raspberry Pi 4B
Defines and initializes all GPIO pins used in the project.
"""

import RPi.GPIO as GPIO

# --- 74HC165 (Parallel-In Serial-Out) — Button Inputs ------------------------
PIN_165_LOAD_PL   = 23   # PL  - load parallel inputs (active LOW)
PIN_165_CLOCK_CP  = 24   # CP  - shift clock
PIN_165_DATA_QH   = 6    # QH  - serial data output to Pi
PIN_165_CE        = 5    # CE  - chip enable (active LOW)

# --- 74HC595 (Serial-In Parallel-Out) — LED Outputs --------------------------
PIN_595_DATA_SER   = 17  # SER   - serial data input from Pi
PIN_595_SHIFT_SRCLK = 22 # SRCLK - shift clock
PIN_595_LATCH_RCLK  = 27 # RCLK  - latch output register
PIN_595_RESET       = 4  # MR    - master reset (active LOW)

# --- MCP2515 CAN Controller ---------------------------------------------------
MCP2515_INT  = 25        # INT - interrupt (active LOW)
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
    print("[GPIO HAL] All pins initialized.")
  
def cleanup_gpio():
    GPIO.cleanup()
    print("[GPIO HAL] GPIO cleaned up.")