import os, subprocess, time, logging
logger = logging.getLogger(__name__)

def start_someipyd(config_path: str):
    socket_path = "/tmp/someipyd.sock"
    if os.path.exists(socket_path):
        os.remove(socket_path)
    logger.warning(f"[DAEMON] Starting someipyd: {config_path}")
    subprocess.Popen(
        ["someipyd", "--config", config_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    for _ in range(50):
        if os.path.exists(socket_path):
            break
        time.sleep(0.1)
    time.sleep(1.0)
    logger.warning("[DAEMON] someipyd ready")
