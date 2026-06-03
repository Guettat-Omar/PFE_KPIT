import sys
import os
import signal
import subprocess
# Add the 'didactic_code' root to Python's path so it can find the 'bcm' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import logging
from bcm.config import DBC_path, CAN_CHANNEL
from bcm.app.gateway import BcmGateway
from bcm.services.flash_timer import FlashTimer
from bcm.services.wbp_monitor import WBPMonitor
from bcm.services.someip_publisher import SomeIPPublisher
from bcm.app.pwf_sm import PWFStateSM
from bcm.utils.systemd_watchdog import SystemdNotifier
from bcm.app.fault_injector import FaultInjector, F1_WBP_TIMEOUT, F2_LSN_TIMEOUT, F3_CAN_E2E_ERROR, F4_PWF_FORCE, F5_WINDOW_BLOCK
from bcm.services.cmd_server import CmdServer
from bcm.services.daemon_launcher import start_someipyd
import logging.handlers

# Mock imports for hardware drivers. 
# We use try/except so we can run this on Windows for testing without Raspberry Pi errors.
try:
    from bcm.drivers.can_driver import init_can, send
    from bcm.drivers.lin_master import init_lin_master, request_frame, close_lin_master, send_frame
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("WARNING: Hardware drivers not found. Running in simulation mode.")
    
logger = logging.getLogger("BCM_MAIN")

def setup_logging():
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    def make_file_handler(filename):
        h = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, filename),
            maxBytes=5 * 1024 * 1024,
            backupCount=3
        )
        h.setFormatter(fmt)
        h.setLevel(logging.INFO)
        return h

    # Root logger  clear any handlers added by imported libraries
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    # Terminal  WARNING and above only (no noise)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(logging.WARNING)
    root.addHandler(console)

    # BCM main log
    bcm_logger = logging.getLogger("BCM_MAIN")
    bcm_logger.addHandler(make_file_handler("bcm_main.log"))
    bcm_logger.propagate = False

    # CAN bus log
    can_logger = logging.getLogger("CAN")
    can_logger.addHandler(make_file_handler("can_bus.log"))
    can_logger.propagate = False

    # LIN bus log
    lin_logger = logging.getLogger("LIN")
    lin_logger.addHandler(make_file_handler("lin_bus.log"))
    lin_logger.propagate = False

    # SOME/IP log
    someip_logger = logging.getLogger("SOMEIP")
    someip_logger.addHandler(make_file_handler("someip.log"))
    someip_logger.propagate = False

    # Suppress internal library noise
    logging.getLogger("someipy").setLevel(logging.ERROR)
    logging.getLogger("websockets").setLevel(logging.ERROR)

# Block someipy and websockets from printing to any handler
    class _SuppressFilter(logging.Filter):
        def filter(self, record):
            return 'someipy' not in record.name and 'websockets' not in record.name

    for handler in root.handlers:
        handler.addFilter(_SuppressFilter())

def main():
    setup_logging()
    start_someipyd("/home/pi2/someipyd_bcm.json")
    logger.warning("=" * 50)
    logger.warning("  BCM NODE STARTING")
    logger.warning("=" * 50)

    # Check serial port
    if not os.path.exists('/dev/serial0'):
        logger.critical("LIN serial port /dev/serial0 not found.")
        sys.exit(1)

    # Check DBC file
    if not os.path.exists(DBC_path):
        logger.critical(f"DBC file not found: {DBC_path}")
        sys.exit(1)

    # Check CAN interface
    result = subprocess.run(['ip','link','show','can0'], capture_output=True)
    if result.returncode != 0:
        logger.critical("CAN interface can0 not found. Bring it up first.")
        sys.exit(1)

    bus = None
    wbp_monitor = WBPMonitor()
    systemd = SystemdNotifier()

    # Initialize PWF state machine
    pwf_sm = PWFStateSM()

    # Initialize SOME/IP Publisher
    publisher = SomeIPPublisher()
    publisher.start()

    # Initialize Fault Injector and Command Server
    fault_injector = FaultInjector()
    cmd_server = CmdServer(fault_injector)

    # 1. Initialize Communication Buses
    if HARDWARE_AVAILABLE:
        bus = init_can()
        init_lin_master('/dev/serial0')
        cmd_server.set_hardware(
            send_lin=send_frame,
            send_can=send
        )
    else:
        logger.warning("Simulation Mode: Hardware buses skipped.")
    cmd_server.start()
    
    def handle_sigterm(signum, frame):
            logger.warning(f"Received Linux signal {signum}. Shutting down safely...")
            systemd.stopping()
            publisher.stop()
            bus.shutdown()
            close_lin_master()
            logger.info("--- BCM Node Shutdown Sequence Complete ---")
            os._exit(0)
    signal.signal(signal.SIGTERM, handle_sigterm)
    # 2. Initialize the Application Layer (Gateway & Timers)
    gw = BcmGateway(DBC_path)
    if not gw.db:
        logger.critical("Cannot start BCM without an active CAN Database.")
        return

    # Create the 1Hz Heartbeat Timer (500ms ON / 500ms OFF)
    flash_timer = FlashTimer(period_ms=500)

    # 3. Enter the Infinite Loop (The BCM Lifecycle)
    logger.warning("BCM entering active run state.")
    
    from bcm.config import (
        LSN_FRAME_ID, LSN_PAYLOAD_LEN, WBP_FRAME_ID, WBP_PAYLOAD_LEN,
        LSN_DIAG_FRAME_ID, LSN_DIAG_LEN, WBP_DIAG_FRAME_ID, WBP_DIAG_LEN
    )

    loop_counter = 0

    wbp_was_healthy = True
    
    # Notify systemd that initialization is complete
    systemd.ready()

    while True:
        try:
            # Pet the watchdog each cycle (every 30ms)
            systemd.pet_watchdog()
            
            loop_counter += 1

            # Step B: Read LIN
            lsn_payload = None
            wbp_payload = None

            is_flashing = flash_timer.update()  # sample flash state just before encoding
            if HARDWARE_AVAILABLE:
                lsn_payload = None if fault_injector.is_active(F2_LSN_TIMEOUT) else request_frame(LSN_FRAME_ID, LSN_PAYLOAD_LEN)
                raw_wbp = None if fault_injector.is_active(F1_WBP_TIMEOUT) else request_frame(WBP_FRAME_ID, WBP_PAYLOAD_LEN)
    
                lsn_valid = lsn_payload is not None and len(lsn_payload) > 0
                wbp_payload = wbp_monitor.update(raw_wbp)
    
                if not lsn_valid:
                    logger.debug("[LSN] No response this cycle.")
                    lsn_payload = b'\x00\x00\x00\x00\x00\x00'
    
                if not wbp_monitor.is_healthy and wbp_was_healthy:
                  logger.warning("[WBP] Node fault  no response for too long.")
                  
                wbp_was_healthy = wbp_monitor.is_healthy
  
                # Step C: Process + Send CAN (only if LSN responded)
                if lsn_valid:
                    can_payload, window_payload, vehicle_state = gw.process_and_send(
                        lsn_payload, wbp_payload, is_flashing, pwf_sm.get_state()
                    )
                    if can_payload is None:
                        logger.warning("[GW] process_and_send returned None, skipping CAN send.")
                        continue
                    logger.debug(f"[GW] lsn={lsn_payload.hex()} wbp={wbp_payload.hex()} payload={can_payload.hex() if can_payload else 'NONE'}")
                    # F3: corrupt CRC byte (index 0 after payload reversal in gateway.py)
                    if fault_injector.is_active(F3_CAN_E2E_ERROR) and can_payload:
                        can_payload = bytearray(can_payload)
                        can_payload[0] ^= 0xFF
                        can_payload = bytes(can_payload)
                        logger.warning("[FAULT] F3: CAN E2E CRC corrupted")

                    if can_payload:
                        can_id = gw.light_cmd_msg.frame_id
                        send(can_id, list(can_payload))
                        logging.getLogger("CAN").info(f"TX ID=0x{can_id:03X} data={bytes(can_payload).hex()}")
                    if window_payload and not fault_injector.is_active(F5_WINDOW_BLOCK):
                        window_id = gw.window_cmd_msg.frame_id
                        send(window_id, list(window_payload))
                        logging.getLogger("CAN").info(f"TX ID=0x{window_id:03X} data={bytes(window_payload).hex()}")
                    elif fault_injector.is_active(F5_WINDOW_BLOCK):
                        logger.warning("[FAULT] F5: Window commands blocked")
                        
                    # Publish SOME/IP state
                    if vehicle_state:
                        # Update PWF state machine and add current state back into dashboard data
                        pwf_request = vehicle_state.pop("pwf_request")
                        current_pwf = pwf_sm.update(pwf_request)
                        if fault_injector.is_active(F4_PWF_FORCE):
                            current_pwf = 0   # force PARKEN regardless of real state
                            logger.warning("[FAULT] F4: PWF forced to PARKEN")
                        vehicle_state["pwf_state"] = current_pwf
                        
                        logger.debug(f"[PWF] Request: {pwf_request} | Active State: {current_pwf}")
                        
                        # Add node health state to vehicle_state
                        vehicle_state["nodes"] = {
                            "bcm": "ONLINE",
                            "lsn": "ONLINE" if lsn_valid else "FAULT",
                            "wbp": "ONLINE" if wbp_monitor.is_healthy else "FAULT"
                        }
                        publisher.publish(vehicle_state)
                else:
                    logger.debug("[GW] LSN non-responsive, skipping CAN send.")
                    publisher.publish({
                        "lights": {"low_beam":0,"high_beam":0,"parking":0,"front_fog":0,"rear_fog":0,"brake":0,"reverse":0},
                        "turn": {"left":0,"right":0,"hazard":0},
                        "windows": {"w1":0,"w2":0,"w3":0,"w4":0},
                        "doors": {"locked":0,"child_safety":0,"fl_open":0,"fr_open":0,"rl_open":0,"rr_open":0},
                        "pwf_state": pwf_sm.get_state(),
                        "nodes": {"bcm":"ONLINE","lsn":"FAULT","wbp":"ONLINE" if wbp_monitor.is_healthy else "FAULT"}
                    })
        
  
                # Step D: Periodic diagnostic
                if loop_counter % 50 == 0:
                    try:
                        lsn_diag_payload = request_frame(LSN_DIAG_FRAME_ID, LSN_DIAG_LEN)
                        wbp_diag_payload = request_frame(WBP_DIAG_FRAME_ID, WBP_DIAG_LEN)

                        if lsn_diag_payload is None:
                            logger.warning("[DIAG] No response from LSN.")
                        else:
                            node_state = lsn_diag_payload[0]
                            can_health = lsn_diag_payload[1]
                            if node_state == 3 or can_health == 0xFF:
                                logger.critical(f"LSN DIAGNOSTIC FAULT: NodeState={node_state}, CAN={can_health}")
                            else:
                                logger.info(f"LSN Health OK: NodeState={node_state}")
                        
                        if wbp_diag_payload is None:
                            logger.warning("[DIAG] No response from WBP.")
                        else:
                            node_state = wbp_diag_payload[0]
                            adc_health = wbp_diag_payload[1]
                            if node_state == 3 or adc_health == 0xFF:
                                logger.critical(f"WBP DIAGNOSTIC FAULT: NodeState={node_state}, ADC={adc_health}")
                            else:
                                logger.info(f"WBP Health OK: NodeState={node_state}")
                    except Exception as diag_err:
                        logger.error(f"[DIAG] Failed: {diag_err}")
  
            else:
                lsn_payload = b'\x00\x00\x00\x00\x00\x00'
                wbp_payload = b'\x00\x00\x00\x00'
  
            time.sleep(0.002)
  
        except KeyboardInterrupt:
            logger.warning("BCM shutting down gracefully...")
            publisher.stop()
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
