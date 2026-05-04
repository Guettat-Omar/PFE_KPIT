import sys
import os
import signal
# Add the 'didactic_code' root to Python's path so it can find the 'bcm' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import logging
from bcm.config import DBC_path, CAN_CHANNEL
from bcm.app.gateway import BcmGateway
from bcm.app.flash_timer import FlashTimer
from bcm.app.wbp_monitor import WBPMonitor
import logging.handlers

# Mock imports for hardware drivers. 
# We use try/except so we can run this on Windows for testing without Raspberry Pi errors.
try:
    from bcm.drivers.can_driver import init_can, send
    from bcm.drivers.lin_master import init_lin_master, request_frame, close_lin_master
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("WARNING: Hardware drivers not found. Running in simulation mode.")
    
logger = logging.getLogger("BCM_MAIN")
logger.setLevel(logging.INFO)

# Define the format of the logs (e.g., "2026-04-09 14:00:00 - INFO: Starting...")
log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

# 1. Create the Rotating File Handler (Max 5MB, keep 3 backup files)
log_path = os.path.join(os.path.dirname(__file__), 'bcm_node.log')
file_handler = logging.handlers.RotatingFileHandler(
    log_path, maxBytes=5*1024*1024, backupCount=3
)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# 2. Keep the Console Handler (so you still see logs if you perfectly run it manually)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

def main():
    logger.info("Starting Body Control Module (BCM)...")
    bus = None
    wbp_monitor = WBPMonitor()

    # 1. Initialize Communication Buses
    if HARDWARE_AVAILABLE:
        # Initialize CAN (e.g., 'can0')
        bus = init_can()
        # Initialize LIN (e.g., '/dev/serial0')
        # We assume baudrate is handled inside init_lin_master via config.py
        init_lin_master('/dev/serial0')
    else:
        logger.warning("Simulation Mode: Hardware buses skipped.")
    
    def handle_sigterm(signum, frame):
            logger.warning(f"Received Linux signal {signum}. Shutting down safely...")
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
    logger.info("BCM entering active run state.")
    
    # Example Node ID from our LDF for LSN input is 0x14, Length is 5 bytes (+1 diag).
    LSN_FRAME_ID = 0x14
    LSN_PAYLOAD_LEN = 6 
    
    # Node ID for Diagnostic Slave Response is 0x3D
    LSN_DIAG_FRAME_ID = 0x3D
    LSN_DIAG_LEN = 8

    loop_counter = 0
    WBP_FRAME_ID = 0x12
    WBP_PAYLOAD_LEN = 4

    WBP_DIAG_FRAME_ID = 0x3E
    WBP_DIAG_LEN = 4

    while True:
      try:
          loop_counter += 1
  
          # Step A: Heartbeat
          is_flashing = flash_timer.update()
  
          # Step B: Read LIN
          lsn_payload = None
          wbp_payload = None
  
          if HARDWARE_AVAILABLE:
              lsn_payload = request_frame(LSN_FRAME_ID, LSN_PAYLOAD_LEN)
              raw_wbp = request_frame(WBP_FRAME_ID, WBP_PAYLOAD_LEN)
  
              lsn_valid = lsn_payload is not None
              wbp_payload = wbp_monitor.update(raw_wbp)
  
              if not lsn_valid:
                  logger.warning("[LSN] No response this cycle.")
                  lsn_payload = b'\x00\x00\x00\x00\x00\x00'
  
              if not wbp_monitor.is_healthy:
                logger.warning("[WBP] Node fault — no response for too long.")
  
              # Step C: Process + Send CAN (only if LSN responded)
              if lsn_valid:
                  result = gw.process_and_send(
                      lsn_payload, wbp_payload, is_flashing
                  )
                  if result is None:
                      logger.warning("[GW] process_and_send returned None, skipping CAN send.")
                      continue
                  can_payload = result[0]
                  window_payload = result[1]
                  print(f"[GW] lsn={lsn_payload.hex()} wbp={wbp_payload.hex()} payload={can_payload.hex() if can_payload else 'NONE'}", flush=True)
                  if can_payload:
                      can_id = gw.light_cmd_msg.frame_id
                      send(can_id, list(can_payload))
                      print(f"[CAN] Sent {can_payload.hex()}", flush=True)
                  if window_payload:
                      window_id = gw.window_cmd_msg.frame_id
                      send(window_id, list(window_payload))
                      print(f"[WINDOW] Sent {window_payload.hex()}", flush=True)
              else:
                  logger.warning("[GW] process_and_send returned None, skipping CAN send.")
        
  
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
          logger.info("BCM shutting down gracefully...")
          break
      except Exception as e:
          logger.error(f"Unexpected error: {e}")
          time.sleep(1)
if __name__ == "__main__":
    main()
