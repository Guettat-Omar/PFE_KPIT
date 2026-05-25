import os
import socket
import logging

logger = logging.getLogger(__name__)

class SystemdNotifier:
    """
    Native implementation for interacting with systemd watchdog and status notifications.
    Doesn't require external pip packages, keeping dependencies light for automotive constraints.
    """
    def __init__(self):
        self.notify_socket_path = os.environ.get("NOTIFY_SOCKET")
        if self.notify_socket_path:
            # Systemd Abstract namespace sockets start with '@'
            if self.notify_socket_path.startswith('@'):
                self.notify_socket_path = '\0' + self.notify_socket_path[1:]
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            logger.info("Systemd Notify Socket found. Watchdog integration active.")
        else:
            self.socket = None
            logger.debug("NOTIFY_SOCKET not set. Running outside of systemd.")

    def _send(self, message: str):
        if self.socket:
            try:
                self.socket.sendto(message.encode(), self.notify_socket_path)
            except Exception as e:
                logger.error(f"Failed to ping systemd: {e}")

    def ready(self):
        """Signals systemd that the service is started and fully initialized."""
        self._send("READY=1")

    def pet_watchdog(self):
        """Resets the systemd watchdog timer. Must be called regularly if WatchdogSec is set."""
        self._send("WATCHDOG=1")
        
    def stopping(self):
        """Signals systemd that the service is shutting down."""
        self._send("STOPPING=1")
