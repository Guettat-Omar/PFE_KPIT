import subprocess
import time
import os
import logging

logger = logging.getLogger(__name__)

def start_someipyd(config_path: str) -> subprocess.Popen:
    """
    Start the someipyd daemon as a background subprocess.
    Waits until the Unix socket appears before returning,
    so the caller knows the daemon is ready to accept connections.
    """
    socket_path = "/tmp/someipyd.sock"

    # If daemon is already running, don't start another one
    if os.path.exists(socket_path):
        logger.info("[DAEMON] someipyd socket already exists — daemon already running")
        return None

    logger.info(f"[DAEMON] Starting someipyd with config: {config_path}")

    proc = subprocess.Popen(
        ["someipyd", "--config", config_path],
        stdout=subprocess.DEVNULL,   # suppress daemon output from BCM log
        stderr=subprocess.DEVNULL,
        start_new_session=True       # daemon survives if BCM restarts
    )

    # Wait up to 5 seconds for the socket to appear
    for _ in range(50):
        if os.path.exists(socket_path):
            break
        time.sleep(0.1)
    time.sleep(1.0)

    logger.error("[DAEMON] someipyd did not start within 5 seconds — check config path")
    return proc