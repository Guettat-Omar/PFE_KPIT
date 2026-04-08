## Plan: Configuration and Logging Implementation (Phase 1)

The goal is to transition the LSN Node from development to production by centralizing configuration (Single Source of Truth) and standardizing logging, stripping away magic numbers and raw `print()` statements.

**Steps**

1. **Create Configuration Component:**
   - Create a `config.py` in the root (`lsn_node/config.py`).
   - Move all GPIO pin constants, Frame IDs (`0x14`, `0x102`, `0x202`), bitrates, and hardware timing settings inside.
   - Refactor `hal/`, `drivers/`, and `app/` modules to import and use these constants.
2. **Implement Logging Module:**
   - Configure Python's standard `logging` in lsn_node/main.py.
   - Replace all scattered `print()` occurrences across layers with appropriate calls to `logging.info()`, `logging.debug()`, and `logging.error()`.
   - _Depends on 1_
3. **Add Receive Timeout:**
   - Update `run()` in lsn_node/app/output_module.py to supply `timeout=1.0` to `bus.recv()`.
   - Log a proper warning when the timeout expires instead of letting the thread hang blindly.

**Relevant files**

- `lsn_node/config.py` (New file) — Centralized configuration repository.
- lsn_node/hal/gpio_hal.py — Replace hardcoded GPIO pins.
- lsn_node/app/output_module.py — Update frame IDs and add thread loop receiver timeout.
- lsn_node/app/input_module.py — Use config variables for LIN IDs.
- lsn_node/main.py — Logger initialization point.

**Verification**

1. Ensure the app successfully runs a cycle just using values from `config.py` with no hardcoded pins or IDs.
2. Monitor log streams (standard output); expect nicely formatted date/time, severity level, and specific module origin rather than basic terminal text.
3. Completely disconnect the CAN line mid-operation. Check logs to confirm the timeout properly catches the unresponsiveness instead of letting `bus.recv()` block permanently.

## Phase 2: Startup Automation (Systemd)

**Goal:** Ensure the absolute reliability of the node without manual intervention on the Raspberry Pi.

1. **CAN Interface Automation:** Create a script or systemd network configuration to automatically bring up `can0` interface on boot with the correct bitrate.
2. **Main Application Service:** Create an `lsn-node.service` file that starts `main.py` automatically and restarts it immediately if the process crashes.

## Phase 3: Error Handling & Robustness

**Goal:** Handle faulty hardware gracefully without freezing the entire system.

1. **Retry Logic:** Implement retry mechanisms for failed LIN/CAN frame transmissions before declaring a hard fault.
2. **Input Validation:** Add checks to all driver functions (e.g., verifying types and bounds of data sent to the 595).
3. **Watchdog Timer:** Implement a software watchdog to catch deadlocks (if code hangs nothing recovers it).
4. **Diagnostics & Reporting:** Send `LSN_Error` frame over LIN/CAN when a fault is detected so the Master knows the node is degraded.
5. **Hardware Response:** Implement hardware unresponsive checks (how do we know if the 165 or 595 is dead?).
6. **CAN Bus-off Recovery:** Implement logic to detect if the MCP2515 enters a BUS-OFF state and attempt a structured reset/recovery.
7. **State Machine:** Implement formal states (INIT -> RUNNING -> FAULT -> RECOVERY).

## Phase 4: Testing & Verification

**Goal:** Prove to the jury it works under stress.

1. **Unit Tests:** Write standalone tests (using `unittest` or `pytest`) for all driver and HAL components.
2. **Fault Injection:** Create scripts to simulate CAN/LIN down states or bad data intentionally.
