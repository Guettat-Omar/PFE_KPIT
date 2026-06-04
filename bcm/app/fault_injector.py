import threading
import logging

logger = logging.getLogger(__name__)

# Fault IDs  must match the dashboard HTML exactly
F1_WBP_TIMEOUT   = 1   # Simulate WBP node not responding
F2_LSN_TIMEOUT   = 2   # Simulate LSN node not responding
F3_CAN_E2E_ERROR = 3   # Corrupt CRC byte on LIGHT_CMD
F4_PWF_FORCE     = 4   # Force PWF state to PARKEN
F5_WINDOW_BLOCK  = 5   # Block all window commands


class FaultInjector:
    """
    Thread-safe fault flag store.

    main.py checks these flags every loop cycle.
    The WebSocket command server sets/clears them from its thread.
    A threading.Lock prevents both threads from reading/writing at the same time.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.lin_freeze = threading.Event()
        self.can_freeze = threading.Event()
        # One boolean flag per fault. False = inactive, True = active.
        self._faults: dict[int, bool] = {
            F1_WBP_TIMEOUT:   False,
            F2_LSN_TIMEOUT:   False,
            F3_CAN_E2E_ERROR: False,
            F4_PWF_FORCE:     False,
            F5_WINDOW_BLOCK:  False,
        }

    def inject(self, fault_id: int) -> bool:
        """Activate a fault. Returns True if the fault ID is valid."""
        with self._lock:
            if fault_id not in self._faults:
                logger.warning(f"[FAULT] Unknown fault ID: {fault_id}")
                return False
            self._faults[fault_id] = True
            logger.warning(f"[FAULT] F{fault_id} INJECTED  {self._name(fault_id)}")
            return True

    def clear(self, fault_id: int) -> bool:
        """Deactivate a single fault."""
        with self._lock:
            if fault_id not in self._faults:
                return False
            self._faults[fault_id] = False
            logger.info(f"[FAULT] F{fault_id} CLEARED  {self._name(fault_id)}")
            return True

    def clear_all(self):
        """Deactivate all faults."""
        with self._lock:
            for fid in self._faults:
                self._faults[fid] = False
        logger.info("[FAULT] ALL FAULTS CLEARED")

    def is_active(self, fault_id: int) -> bool:
        """Read a fault flag. Called from main loop every 10ms."""
        with self._lock:
            return self._faults.get(fault_id, False)

    def active_faults(self) -> list[int]:
        """Return list of currently active fault IDs."""
        with self._lock:
            return [fid for fid, active in self._faults.items() if active]

    @staticmethod
    def _name(fault_id: int) -> str:
        names = {
            1: "WBP NODE TIMEOUT",
            2: "LSN NODE TIMEOUT",
            3: "CAN E2E ERROR",
            4: "PWF STATE FORCE",
            5: "WINDOW BLOCKED",
        }
        return names.get(fault_id, "UNKNOWN")