"""
Main Entry Point - LSN Node
Initializes hardware, configures logging, and starts the LIN and CAN background threads.

LAYER: Application Layer
NODE: LSN Node | Raspberry Pi 4B
"""

import threading
import logging
from config import LIN_frame_id

from hal.gpio_hal import init_gpio, cleanup_gpio
from drivers.lin_slave import register_handler, start
from app.input_module import handle_input_request
from app.output_module import init as can_init, run

logger = logging.getLogger(__name__)

def main():
    # Configure the logger to output to BOTH the file and the terminal!
    logging.basicConfig(
        level=logging.INFO, 
        format='[%(asctime)s] %(name)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler("lsn.log"),
            logging.StreamHandler()
        ]
    )
    logger.info("--- LSN Node Startup Sequence Initiated ---")
    
    logger.info("Initializing GPIO HAL layer...")
    init_gpio()
    
    logger.info(f"Registering LIN handler for frame ID {hex(LIN_frame_id)}...")
    register_handler(LIN_frame_id, handle_input_request)
    
    logger.info("Initializing CAN bus...")
    bus = can_init()

    
    # create 2 threads
    logger.info("Starting background threads for LIN and CAN routines...")
    lin_thread = threading.Thread(target=start, daemon=True)
    can_thread = threading.Thread(target=run, args=(bus,), daemon=True)
    
    try:
        # start both threads
        lin_thread.start()
        can_thread.start()
        
        logger.info("LSN Node is now fully running. Waiting for interrupts...")
        # keep main alive (LIN thread runs process_frames in a loop)
        while True:
            lin_thread.join(1)
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt detected. Shutting down system safely...")
        cleanup_gpio()
        logger.info("--- LSN Node Shutdown Sequence Complete ---")
        os._exit(0)  # Instantly kill daemon threads to prevent GPIO race conditions

if __name__ == '__main__':
    main()