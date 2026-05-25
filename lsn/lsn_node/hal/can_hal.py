import subprocess
import logging
import time

logger = logging.getLogger(__name__)

def reset_can_interface(interface="can0", bitrate=500000):
    """
    Hardware Abstraction Layer (HAL) function.
    Self-heals the CAN interface at the OS level, isolating 
    the Application layer from direct system OS calls.
    """
    try:
        subprocess.run(["sudo", "ip", "link", "set", interface, "down"], capture_output=True)
        subprocess.run(["sudo", "ip", "link", "set", interface, "type", "can", "bitrate", str(bitrate)], capture_output=True)
        result = subprocess.run(["sudo", "ip", "link", "set", "up", interface], capture_output=True, text=True)
        
        logger.info(f"[HAL] Self-healing ip commands executed for {interface}.")
        if result.stderr:
            logger.error(f"[HAL] Self-healing ip errors: {result.stderr.strip()}")
        
        # Give the OS 1 second to actually turn the hardware on before Python tries to bind to it!
        time.sleep(1)
        return True
    except Exception as e:
        logger.error(f"[HAL] Failed to reset CAN interface: {e}")
        return False