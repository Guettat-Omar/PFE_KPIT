import threading
from hal.gpio_hal import init_gpio, cleanup_gpio
from drivers.lin_slave import register_handler, start
from app.input_module import  handle_input_request
from app.output_module import init as can_init, run
from config import LIN_frame_id
import logging
logger = logging.getLogger(__name__)
def main():
    logging.basicConfig(filename='lsn.log',level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    init_gpio()
    # register LIN handler
    register_handler(LIN_frame_id, handle_input_request)
    
    # init CAN bus
    bus = can_init()

    
    # create 2 threads
    lin_thread = threading.Thread(target=start)
    can_thread = threading.Thread(target=run, args=(bus,))
    
    try:
        # start both threads
        lin_thread.start()
        can_thread.start()
        # keep main alive
        lin_thread.join()
    except KeyboardInterrupt:
        cleanup_gpio()
if __name__ == '__main__':
    main()