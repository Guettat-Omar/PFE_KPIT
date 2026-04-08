import time
import logging
import sys
import os

# Setup dynamic local paths for testing (no hardcoded folders)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from hal.gpio_hal import init_gpio, cleanup_gpio
from drivers.hc165_driver import read_all_chips

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def test_hc165():
    logging.info("==================================================")
    logging.info("    PHASE 4: 74HC165 INPUT DRIVER HIL TEST")
    logging.info("==================================================")
    
    try:
        init_gpio()
        logging.info("GPIO Initialized Successfully.")
        logging.info("Starting live polling for 15 seconds...")
        logging.info(">>> PRESS YOUR SWITCHES/BUTTONS NOW! <<<")
        
        previous_data = None
        
        # Read the chips 15 times, once per second
        for i in range(15):
            # We expect 5 cascaded chips based on your architecture
            chips_data = read_all_chips(5)
            
            if chips_data != previous_data:
                # Convert to binary strings so it is easy to see exactly which pin toggled
                binary_strings = ["{0:08b}".format(b) for b in chips_data]
                logging.info(f"Time: {i+1}s | CHANGE DETECTED!")
                logging.info(f"   Hex:  {[hex(b) for b in chips_data]}")
                logging.info(f"   Bits: {binary_strings}")
                previous_data = chips_data
            else:
                logging.info(f"Time: {i+1}s | No changes...")
                
            time.sleep(1)
            
        logging.info("==================================================")
        logging.info("✅ 74HC165 HARDWARE VERIFICATION COMPLETE")
        logging.info("==================================================")
        
    except KeyboardInterrupt:
        logging.info("Test halted by user.")
    except Exception as e:
        logging.error(f"Hardware Test Failed: {e}")
    finally:
        cleanup_gpio()
        logging.info("GPIO Cleaned up. Exiting.")

if __name__ == "__main__":
    test_hc165()