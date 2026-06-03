"""
Main Entry Point - LSN Node
Initializes hardware, configures logging, and starts the LIN and CAN background threads.

LAYER: Application Layer
NODE: LSN Node | Raspberry Pi 4B
"""

import threading
import logging
import os
import signal
import time
from config import LIN_frame_id, NodeState
import config
from hal.gpio_hal import init_gpio, cleanup_gpio
from drivers.hc595_driver import write_all_chips
from drivers.lin_slave import register_handler, start
from app.input_module import handle_input_request, handle_diagnostic_request, check_lin_watchdog
from app.output_module import init as can_init, run

logger = logging.getLogger(__name__)

def setup_logging():
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    def make_handler(filename):
        import logging.handlers
        h = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, filename),
            maxBytes=5 * 1024 * 1024,
            backupCount=3
        )
        h.setFormatter(fmt)
        h.setLevel(logging.INFO)
        return h

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    # Terminal — WARNING only
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(logging.WARNING)
    root.addHandler(console)

    # General LSN log
    root.addHandler(make_handler("lsn_main.log"))

    # Communications log — LIN and CAN frames
    comm_logger = logging.getLogger("communication")
    comm_logger.addHandler(make_handler("communications.log"))
    comm_logger.propagate = False


def main():
    setup_logging()
    logger.warning("=" * 50)
    logger.warning("  LSN NODE STARTING")
    logger.warning("=" * 50)
    
    logger.info("Initializing GPIO HAL layer...")
    init_gpio()
    
    logger.info(f"Registering LIN handler for frame ID {hex(LIN_frame_id)}...")
    register_handler(LIN_frame_id, handle_input_request)
    
    logger.info(f"Registering Diagnostic LIN handler for frame ID 0x3D...")
    register_handler(0x3D, handle_diagnostic_request)
    
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
        
        def handle_sigterm(signum, frame):
            logger.warning(f"Received Linux signal {signum}. Shutting down safely...")
            cleanup_gpio()
            logger.info("--- LSN Node Shutdown Sequence Complete ---")
            os._exit(0)
            
        # Map the Linux Termination signal from systemd to our clean shutdown function
        signal.signal(signal.SIGTERM, handle_sigterm)
        
        logger.info("LSN Node is now fully running. Waiting for interrupts...")
        config.current_node_state = NodeState.RUNNING
        
        # keep main alive and act as the global state supervisor
        fault_toggle = False
        was_in_fault_state = False
        
        while True:
            # Continuously check if the LIN master died
            check_lin_watchdog()
            
            # Check the global state machine 
            if config.current_node_state == NodeState.FAULT:
                # Log the transition only once when we enter the FAULT state
                if not was_in_fault_state:
                    logger.critical(f"SYSTEM STATE CHANGED TO: FAULT. Reason: {config.last_fault_reason}. Initiating SOS flashing sequence.")
                    was_in_fault_state = True
                    
                # Option 3: Flash LEDs synchronously at 1Hz as a visual SOS
                if fault_toggle:
                    with config.chips_lock:  # Ensure thread-safe access to the chips
                        write_all_chips([0xFF] * 5) # All ON
                else:
                    with config.chips_lock:  # Ensure thread-safe access to the chips
                        write_all_chips([0x00] * 5) # All OFF
                
                fault_toggle = not fault_toggle
                time.sleep(1) # Flash explicitly at 1Hz
            elif config.current_node_state == NodeState.RECOVERY:
                logger.warning(f"SYSTEM STATE RECOVERY: Attempting to heal hardware... Reason: {config.last_fault_reason}")
                time.sleep(2)  # Give the system time to bounce before checking again
                
            else:
                # If we recover, reset the fault state tracker
                if was_in_fault_state:
                    logger.info("SYSTEM STATE CHANGED TO: RUNNING. Hardware recovered.")
                    was_in_fault_state = False
                    
                lin_thread.join(1)
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt detected. Shutting down system safely...")
        cleanup_gpio()
        logger.info("--- LSN Node Shutdown Sequence Complete ---")
        os._exit(0)  # Instantly kill daemon threads to prevent GPIO race conditions

if __name__ == '__main__':
    main()