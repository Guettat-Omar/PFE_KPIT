import threading
from hal.gpio_hal import init_gpio, cleanup_gpio
from drivers.lin_slave import register_handler, start
from app.input_module import  handle_input_request
from app.output_module import init as can_init, run

if __name__ == '__main__':
    init_gpio()
    
    # register LIN handler
    register_handler(0x14, handle_input_request)
    
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