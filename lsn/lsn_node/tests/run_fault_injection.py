# ==============================================================================
# Phase 4: Full System Fault Injection & E2E Validation Script
# Run this script ON THE NODE ITSELF alongside your master node.
# It acts like a "virus"/inspector to forcefully test state transitions!
# ==============================================================================

import time
import os
import subprocess
import can
import logging

# We set up a quick local logger to see the chaos unfolding
logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] EVIL_TESTER - %(levelname)s: %(message)s'
)
t_logger = logging.getLogger("tester")

def test_1_can_timeout_fault():
    """
    Test Step 1: Forcefully pull down the physical CAN interface.
    This simulates a broken CAN wire. We expect the watchdog to trigger FAULT
    and then self-heal.
    """
    t_logger.warning(">>> TEST 1 INITIATED: KILLING CAN BUS (Simulating cut wire) <<<")
    # Tell Linux to literally shut off the CAN port hardware
    os.system("sudo ip link set can0 down")
    
    t_logger.info("CAN bus is down. Waiting 6 seconds to see if Output Module triggers FAULT and Self-Heals...")
    
    # We wait 6 seconds because our Watchdog is hardcoded to 5.0 seconds
    time.sleep(6)
    
    # Let's check Linux to see if our node's python script successfully ran `can_init.sh` to heal itself!
    result = subprocess.run(['ip', 'link', 'show', 'can0'], capture_output=True, text=True)
    if "UP" in result.stdout:
        t_logger.info("✅ SUCCESS: The CAN bus successfully self-healed!")
    else:
        t_logger.error("❌ FAILED: The CAN bus did NOT self-heal within 6 seconds.")
        # We bring it back up manually so we don't break the whole test suite
        os.system("sudo ip link set up can0")

def test_2_lin_upstream_diagnostic():
    """
    Test Step 2: Since the Master is connected, IF we drop the CAN bus again, 
    does the LIN module properly append 0xFF to the payload?
    """
    t_logger.warning(">>> TEST 2 INITIATED: VERIFYING LIN DIAGNOSTIC ERROR TRANSMISSION <<<")
    # Kill the bus again just to trigger the global state fault logic
    os.system("sudo ip link set can0 down")
    
    t_logger.info("CAN down. The global node state should be FAULT now.")
    t_logger.info("PLEASE CHECK YOUR LIN MASTER LOGS RIGHT NOW!")
    t_logger.info("You should see the 6th byte of the LIN payload change from 0x00 to 0xFF.")
    
    # Give the user a moment to verify it on their master screen
    time.sleep(10)
    
    t_logger.info("Healing CAN bus before proceeding...")
    os.system("sudo sh /home/pi/lsn/can_init.sh")

def start_full_e2e_tests():
    t_logger.info("=== STARTING FULL END-TO-END VALIDATION SUITE ===")
    t_logger.info("MAKE SURE YOUR SYSTEMD SERVICE (lsn-node) IS ACTIVELY RUNNING IN THE BACKGROUND!")
    t_logger.info("Also ensure your LIN/CAN Master node is running and polling.")
    
    time.sleep(3)
    
    test_1_can_timeout_fault()
    time.sleep(2)
    test_2_lin_upstream_diagnostic()
    
    t_logger.info("=== FULL END-TO-END SUITE COMPLETE ===")
    t_logger.info("If the master received the 0xFF byte, and the LEDs flashed during the fault, Phase 4 is 100% complete.")

if __name__ == "__main__":
    start_full_e2e_tests()