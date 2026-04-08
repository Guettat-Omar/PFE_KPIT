
import RPi.GPIO as GPIO
import logging

from bcm.config import MCP2515_INT
logger = logging.getLogger(__name__)

def init_gpio():
    GPIO.setmode(GPIO.BCM)
    # Initialize GPIO pins here
    GPIO.setup(MCP2515_INT,GPIO.IN)
    logger.info("[GPIO HAL] All pins initialized.")
def cleanup_gpio():
    GPIO.cleanup()
    logger.info("[GPIO HAL] GPIO cleaned up.")