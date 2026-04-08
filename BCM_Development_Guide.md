# BCM Node — Complete Development Guide
### Raspberry Pi 4B | LIN Master + CAN Node | Central Gateway | v4.0
### PFE 2025 | Automotive Didactic Platform

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Teaching Methodology](#2-teaching-methodology)
3. [Senior Embedded Engineer Best Practices](#3-senior-embedded-engineer-best-practices)
4. [Software Architecture](#4-software-architecture)
5. [Folder Structure](#5-folder-structure)
6. [What Needs To Be Built](#6-what-needs-to-be-built)
7. [Build Order — Layer by Layer](#7-build-order--layer-by-layer)
8. [State Machines Specification](#8-state-machines-specification)
9. [LIN Schedule Specification](#9-lin-schedule-specification)
10. [CAN Frame Specification](#10-can-frame-specification)
11. [Production Checklist](#11-production-checklist)
12. [Jury Defense Preparation](#12-jury-defense-preparation)

---

## 1. Project Overview

The BCM (Body Control Module) is the **central gateway** of the automotive didactic platform. It runs on Raspberry Pi 4B Unit 1 and has two roles simultaneously:

- **LIN Master** — schedules and polls all LIN slave nodes (SCS, WBP, WPA, LSN) on a 30ms cycle
- **CAN Node** — sends commands to CAN actuator nodes (Window, Door Lock, LSN) and receives their status

### System Context

```
LIN Bus (19.2 kbit/s)
├── SCS Node (Arduino)   → BCM reads SCS_Status   0x11
├── WBP Node (Arduino)   → BCM reads WBP_Status   0x12 / ButtonEvent 0x30
├── WPA Node (Arduino)   ← BCM sends WPA_Command  0x01
│                        → BCM reads WPA_Status   0x13
└── LSN Node (RPi 4B)   → BCM reads LSN_Input    0x14

CAN Bus (500 kbit/s)
├── Window Node (Arduino) ← BCM sends WINDOW_CMD    0x101
│                         → BCM reads WINDOW_STATUS 0x201
├── Door Lock Node (Arduino) ← BCM sends DOOR_LOCK_CMD    0x100
│                            → BCM reads DOOR_LOCK_STATUS 0x200
└── LSN Node (RPi 4B)   ← BCM sends LIGHT_CMD     0x102
                         → BCM reads LIGHT_STATUS  0x202
```

### BCM Responsibilities

- Read all LIN input frames every 30ms
- Run 9 state machines based on input signals
- Send CAN commands based on state machine outputs
- Send LIN commands to WPA node
- Handle faults: timeout, checksum error, framing error

---

## 2. Teaching Methodology

This project is built using a **Socratic embedded engineering methodology**. Every session follows these rules strictly:

### Rules for the Student

- **Never copy-paste code without understanding it.** Every line must be explainable.
- **Write code yourself first.** The teacher asks questions before showing solutions.
- **Test every layer before moving to the next.** Never trust, always verify on hardware.
- **Know the WHY behind every decision.** Not just the HOW.

### Rules for the Teacher/Supervisor

- Ask questions before giving answers. Force the student to think.
- Point to the exact mistake and explain why it is wrong. Make the student fix it.
- Never give complete code unless the student is completely stuck or has no time.
- After every concept: ask "how would you explain this to your jury?"
- Build bottom-up: HAL → Drivers → App. Never skip layers.
- Test after every module with a standalone script before moving on.

### Session Workflow

```
1. Teacher states the goal for the session
2. Teacher asks: what should this function do? inputs? outputs? why?
3. Student attempts to write it
4. Teacher reviews: correct mistakes with explanation
5. Student fixes and explains the correction
6. Run test on real hardware
7. Confirm working before moving to next function
```

---

## 3. Senior Embedded Engineer Best Practices

These are non-negotiable for a production-quality embedded system. Apply them from day one.

### 3.1 Centralized Configuration

Never scatter magic numbers across files. All constants live in `config.py`:

```python
# config.py
# LIN
LIN_BAUD_RATE        = 19200
LIN_SCHEDULE_CYCLE   = 0.030       # 30ms
LIN_SLOT_DURATION    = 0.005       # 5ms per slot

# LIN Frame IDs
LIN_FRAME_SCS_STATUS  = 0x11
LIN_FRAME_WPA_CMD     = 0x01
LIN_FRAME_WPA_STATUS  = 0x13
LIN_FRAME_BTN_EVENT   = 0x30
LIN_FRAME_LSN_INPUT   = 0x14

# CAN
CAN_BITRATE           = 500000
CAN_CHANNEL           = 'can0'

# CAN Frame IDs TX
CAN_DOOR_LOCK_CMD     = 0x100
CAN_WINDOW_CMD        = 0x101
CAN_LIGHT_CMD         = 0x102

# CAN Frame IDs RX
CAN_DOOR_LOCK_STATUS  = 0x200
CAN_WINDOW_STATUS     = 0x201
CAN_LIGHT_STATUS      = 0x202

# Flash timer
FLASH_PERIOD          = 0.500      # 500ms turn signal / hazard

# DRL threshold
DRL_LDR_THRESHOLD     = 512        # out of 1023
```

### 3.2 Proper Logging — Never Use print()

```python
import logging

log = logging.getLogger(__name__)

# Use levels correctly:
log.debug("SCS status received: %s", data)       # detailed trace
log.info("LIN schedule started")                  # normal operation
log.warning("LIN slot overrun: %.1f ms", overrun) # degraded but running
log.error("LIN timeout on frame 0x%02X", fid)    # recoverable fault
log.critical("CAN bus-off — node suspended")      # unrecoverable fault
```

Configure once in `main.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/var/log/bcm.log'),
        logging.StreamHandler()
    ]
)
```

### 3.3 Input Validation on Every Driver Function

```python
def send_light_cmd(data: list[int]) -> None:
    if len(data) != 1:
        raise ValueError(f"LIGHT_CMD expects 1 byte, got {len(data)}")
    if not 0 <= data[0] <= 0xFF:
        raise ValueError(f"Invalid byte value: {data[0]}")
```

### 3.4 Type Hints on All Functions

```python
from typing import Optional

def request_lin_frame(frame_id: int, length: int) -> Optional[bytes]:
    ...

def send_can_frame(arb_id: int, data: list[int]) -> bool:
    ...
```

### 3.5 Defensive Programming — Handle Every Failure

```python
# WRONG — crashes on timeout:
data = lin.request_data(0x14, expected_data_length=5)
process(data)

# CORRECT — always handle failure:
try:
    data = lin.request_data(0x14, expected_data_length=5)
    process(data)
except LINTimeoutError:
    log.error("LSN_Input timeout — retrying")
    fault_handler.report(FAULT_LSN_TIMEOUT)
except LINChecksumError:
    log.error("LSN_Input checksum error")
    fault_handler.report(FAULT_LSN_CHECKSUM)
```

### 3.6 State Machines — Always Explicit States

Never use boolean flags to represent states. Use enums:

```python
from enum import Enum, auto

class TurnSignalState(Enum):
    IDLE    = auto()
    LEFT    = auto()
    RIGHT   = auto()
    HAZARD  = auto()
```

### 3.7 Layer Discipline — Enforced Always

```
app/      → imports from drivers/ only. NEVER from hal/ directly.
drivers/  → imports from hal/ only. NEVER from app/.
hal/      → imports nothing from the project. Only stdlib and system libs.
config.py → imported by all layers. Contains only constants, no logic.
```

### 3.8 Resource Management

Always release resources on exit:

```python
try:
    run_bcm()
except KeyboardInterrupt:
    log.info("BCM shutdown requested")
finally:
    can_bus.shutdown()
    lin_master.close()
    cleanup_gpio()
    log.info("BCM shutdown complete")
```

### 3.9 Timeout on Every Blocking Call

```python
# WRONG — blocks forever if node is dead:
msg = bus.recv()

# CORRECT — always use timeout:
msg = bus.recv(timeout=0.1)
if msg is None:
    log.warning("CAN recv timeout")
    return None
```

### 3.10 Startup Automation with systemd

Create `/etc/systemd/system/bcm.service`:

```ini
[Unit]
Description=BCM Node
After=network.target

[Service]
ExecStartPre=/sbin/ip link set can0 up type can bitrate 500000
ExecStart=/usr/bin/python3 /home/pi/bcm_node/main.py
Restart=always
RestartSec=3
User=pi

[Install]
WantedBy=multi-user.target
```

Enable with:
```bash
sudo systemctl enable bcm
sudo systemctl start bcm
```

---

## 4. Software Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                          │
│                                                                 │
│  turn_signal_sm.py   headlight_sm.py   brake_sm.py             │
│  reverse_sm.py       wiper_sm.py       washer_sm.py            │
│  door_lock_sm.py     window_sm.py      drl_sm.py               │
│                         gateway.py                              │
├─────────────────────────────────────────────────────────────────┤
│                       SERVICE LAYER                             │
│  (part of drivers/ in implementation)                           │
│  flash_timer.py      fault_handler.py                          │
├─────────────────────────────────────────────────────────────────┤
│                       DRIVERS LAYER                             │
│  lin_master.py       can_driver.py                             │
├─────────────────────────────────────────────────────────────────┤
│                          HAL LAYER                              │
│  gpio_hal.py         uart_hal.py                               │
├─────────────────────────────────────────────────────────────────┤
│                         HARDWARE                                │
│  UART → TJA1020 → LIN bus                                      │
│  SPI → MCP2515 → TJA1050 → CAN bus                            │
└─────────────────────────────────────────────────────────────────┘

Rule: Each layer calls only the layer directly below it.
      config.py is imported by all layers (constants only).
```

---

## 5. Folder Structure

```
/home/pi/bcm_node/
├── main.py                    ← entry point, threading, init order
├── config.py                  ← ALL constants (frame IDs, timings, pins)
├── hal/
│   ├── __init__.py
│   └── gpio_hal.py            ← GPIO pin init, cleanup
├── drivers/
│   ├── __init__.py
│   ├── lin_master.py          ← LIN schedule loop, frame TX/RX
│   ├── can_driver.py          ← CAN send/recv wrapper
│   ├── flash_timer.py         ← 500ms software timer for turn/hazard
│   └── fault_handler.py       ← LIN/CAN fault tracking and retry
└── app/
    ├── __init__.py
    ├── gateway.py             ← main logic: reads LIN, runs SMs, sends CAN
    ├── turn_signal_sm.py      ← Turn Signal state machine
    ├── headlight_sm.py        ← Headlight state machine
    ├── brake_sm.py            ← Brake Light state machine
    ├── reverse_sm.py          ← Reverse Light state machine
    ├── wiper_sm.py            ← Wiper Control state machine
    ├── washer_sm.py           ← Washer state machine
    ├── door_lock_sm.py        ← Door Lock state machine
    ├── window_sm.py           ← Window Control state machine
    └── drl_sm.py              ← DRL state machine (v2 — LDR sensor)
```

---

## 6. What Needs To Be Built

### Phase 1 — BCM + LSN Only (Start Here)

Goal: button press on LSN → BCM reads via LIN → BCM sends LIGHT_CMD via CAN → LED lights up.

| File | Status | Description |
|------|--------|-------------|
| `config.py` | ⏳ TODO | All constants centralized |
| `hal/gpio_hal.py` | ⏳ TODO | GPIO init for BCM pins |
| `drivers/lin_master.py` | ⏳ TODO | LIN schedule — slot 5 only (LSN_Input 0x14) |
| `drivers/can_driver.py` | ⏳ TODO | CAN send LIGHT_CMD 0x102, recv LIGHT_STATUS 0x202 |
| `app/turn_signal_sm.py` | ⏳ TODO | Turn signal logic from LSN button bits |
| `app/headlight_sm.py` | ⏳ TODO | Headlight logic from LSN button bits |
| `app/brake_sm.py` | ⏳ TODO | Brake light logic from LSN button bits |
| `app/reverse_sm.py` | ⏳ TODO | Reverse light logic from LSN button bits |
| `app/gateway.py` | ⏳ TODO | Reads LSN_Input, runs SMs, sends LIGHT_CMD |
| `main.py` | ⏳ TODO | Init + threading |

### Phase 2 — Add SCS + WPA Nodes

| File | Status | Description |
|------|--------|-------------|
| `drivers/lin_master.py` | 🔄 EXTEND | Add slots 1, 2, 3 (SCS, WPA_Cmd, WPA_Status) |
| `app/wiper_sm.py` | ⏳ TODO | Wiper SM from SCS_Status bits |
| `app/washer_sm.py` | ⏳ TODO | Washer SM from SCS_Status bits |
| `app/gateway.py` | 🔄 EXTEND | Add WPA logic |

### Phase 3 — Add WBP Node

| File | Status | Description |
|------|--------|-------------|
| `drivers/lin_master.py` | 🔄 EXTEND | Add slots 4 (ButtonEvent 0x30) |
| `app/door_lock_sm.py` | ⏳ TODO | Door lock SM from WBP buttons |
| `app/window_sm.py` | ⏳ TODO | Window SM from WBP buttons |
| `drivers/can_driver.py` | 🔄 EXTEND | Add DOOR_LOCK_CMD, WINDOW_CMD |
| `app/gateway.py` | 🔄 EXTEND | Add door + window logic |

### Phase 4 — Flash Timer + DRL

| File | Status | Description |
|------|--------|-------------|
| `drivers/flash_timer.py` | ⏳ TODO | 500ms toggle for turn/hazard |
| `app/drl_sm.py` | ⏳ TODO | DRL from LDR sensor (v2) |

### Phase 5 — Production Hardening

| File | Status | Description |
|------|--------|-------------|
| `drivers/fault_handler.py` | ⏳ TODO | LIN retry + fault flags |
| All files | 🔄 REVIEW | Replace print() with logging |
| All driver functions | 🔄 REVIEW | Add input validation |
| `systemd` service | ⏳ TODO | Auto-start on boot |

---

## 7. Build Order — Layer by Layer

### Step 1 — config.py

Write all constants first. No code runs without this.
Test: `python3 -c "from config import *; print(LIN_FRAME_LSN_INPUT)"`

### Step 2 — hal/gpio_hal.py

BCM has fewer GPIO pins than LSN — mainly UART and SPI are kernel managed.
Test: `python3 test_gpio.py` — confirm no errors on init and cleanup.

### Step 3 — drivers/lin_master.py

Wraps `lin_protocol.LINMaster`. Exposes:
- `init()` → returns master instance
- `request_frame(frame_id, length)` → returns bytes or None
- `send_frame(frame_id, data)` → sends command frame

Test: `python3 test_lin_master.py` — request LSN_Input 0x14, print result.

### Step 4 — drivers/can_driver.py

Wraps `python-can`. Exposes:
- `init()` → returns bus instance
- `send(arb_id, data)` → sends CAN frame
- `recv(timeout)` → returns message or None

Test: `python3 test_can_driver.py` — send LIGHT_CMD, confirm LSN LEDs light up.

### Step 5 — app/turn_signal_sm.py (and other SMs)

Each SM is a class with:
- `update(lsn_input_byte)` → reads input bits, updates state
- `get_light_cmd_byte()` → returns LED output byte

Test: unit test with fake input bytes — no hardware needed.

### Step 6 — app/gateway.py

The main logic loop:
1. Request LSN_Input via LIN
2. Pass data to all state machines
3. Collect LED output from all SMs
4. Send LIGHT_CMD via CAN

Test: full end-to-end — press button on LSN, confirm LED lights on LSN.

### Step 7 — main.py

Threading: LIN loop + CAN recv loop running simultaneously.
Init order: GPIO → LIN → CAN → SMs → Gateway → Start threads.

---

## 8. State Machines Specification

### Turn Signal SM

```
States: IDLE, LEFT, RIGHT, HAZARD

Transitions:
  IDLE    + left_btn pressed   → LEFT
  IDLE    + right_btn pressed  → RIGHT
  IDLE    + hazard_btn pressed → HAZARD
  LEFT    + left_btn released  → IDLE
  RIGHT   + right_btn released → IDLE
  HAZARD  + hazard_btn pressed → IDLE  (toggle off)

Output (LIGHT_CMD bit mapping):
  LEFT:   bit 0 = flash (500ms timer)
  RIGHT:  bit 1 = flash (500ms timer)
  HAZARD: bit 0 + bit 1 = flash together
```

### Headlight SM

```
States: ALL_OFF, PARKING, LOW_BEAM, HIGH_BEAM

Transitions (priority: HIGH > LOW > PARKING > OFF):
  ALL_OFF   + parking_sw  → PARKING
  PARKING   + low_sw      → LOW_BEAM
  LOW_BEAM  + high_sw     → HIGH_BEAM
  HIGH_BEAM + high_sw     → LOW_BEAM   (toggle)
  ANY       + same_sw off → previous state

Output:
  PARKING:  bit 7 = 1
  LOW_BEAM: bit 2 = 1, bit 7 = 1
  HIGH_BEAM: bit 3 = 1, bit 7 = 1
```

### Brake Light SM

```
States: BRAKE_OFF, BRAKE_ON

Transitions:
  BRAKE_OFF + brake_btn pressed  → BRAKE_ON
  BRAKE_ON  + brake_btn released → BRAKE_OFF

Output: bit 5 = state
```

### Reverse Light SM

```
States: REVERSE_OFF, REVERSE_ON

Transitions:
  REVERSE_OFF + reverse_btn pressed  → REVERSE_ON
  REVERSE_ON  + reverse_btn released → REVERSE_OFF

Output: bit 6 = state
```

### LIGHT_CMD Byte Composition (0x102)

```
Bit 0 → Left Turn Signal LED
Bit 1 → Right Turn Signal LED
Bit 2 → Low Beam LED
Bit 3 → High Beam LED
Bit 4 → DRL LED
Bit 5 → Brake Light LED
Bit 6 → Reverse Light LED
Bit 7 → Parking Light LED

Gateway ORs all SM outputs into one byte before sending.
```

---

## 9. LIN Schedule Specification

```
Cycle: 30ms total | 6 slots × 5ms each

Slot 1 (t=0ms)   → Request SCS_Status   0x11  (1 byte response)
Slot 2 (t=5ms)   → Send    WPA_Command  0x01  (1 byte command)
Slot 3 (t=10ms)  → Request WPA_Status   0x13  (1 byte response)
Slot 4 (t=15ms)  → Request ButtonEvent  0x30  (2 byte response — event)
Slot 5 (t=20ms)  → Request LSN_Input    0x14  (5 bytes response)
Slot 6 (t=25ms)  → Request LSN_Sensors  0x15  (2 bytes — v2 deferred)

Phase 1: implement slot 5 only.
Phase 2: add slots 1, 2, 3.
Phase 3: add slot 4.
Phase 4: add slot 6 (v2).
```

### Schedule Loop Pattern

```python
while True:
    cycle_start = time.monotonic()

    # Slot 5 — Phase 1 only
    lsn_data = lin_master.request_frame(LIN_FRAME_LSN_INPUT, 5)
    if lsn_data:
        gateway.process_lsn_input(lsn_data)

    # Wait for next cycle
    elapsed = time.monotonic() - cycle_start
    remaining = LIN_SCHEDULE_CYCLE - elapsed
    if remaining > 0:
        time.sleep(remaining)
    else:
        log.warning("Schedule overrun: %.1f ms", abs(remaining) * 1000)
```

---

## 10. CAN Frame Specification

### TX Frames (BCM sends)

| Frame | ID | Data | Trigger |
|-------|----|------|---------|
| DOOR_LOCK_CMD | 0x100 | 1 byte: bit0=LockCmd | Event (button press) |
| WINDOW_CMD | 0x101 | 1 byte: bits[1:0]=Left, bits[3:2]=Right | Event |
| LIGHT_CMD | 0x102 | 1 byte: 8 LED bits | Event + 500ms flash |

### RX Frames (BCM receives)

| Frame | ID | Data | Period |
|-------|----|------|--------|
| DOOR_LOCK_STATUS | 0x200 | 1 byte: bit0=state, bit1=fault | 20ms |
| WINDOW_STATUS | 0x201 | 1 byte: motor states + faults | 20ms |
| LIGHT_STATUS | 0x202 | 1 byte: mirrors LED states | 20ms |

---

## 11. Production Checklist

Before calling this project production-ready, verify every item:

### Code Quality
- [ ] All magic numbers removed — only `config.py` constants used
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] No `print()` anywhere — only `logging`
- [ ] All blocking calls have timeouts
- [ ] All driver functions have input validation
- [ ] Layer discipline respected — app never imports hal

### Robustness
- [ ] LIN timeout handled on every frame request
- [ ] LIN checksum error handled and logged
- [ ] CAN bus-off recovery implemented
- [ ] Fault handler retries once before suspending node
- [ ] Node recovers automatically after transient fault

### Startup
- [ ] `can0` brought up automatically via systemd
- [ ] `main.py` starts automatically on boot
- [ ] Process restarts automatically if it crashes
- [ ] Log file written to `/var/log/bcm.log`

### Testing
- [ ] Each driver tested standalone before integration
- [ ] Each state machine unit tested with fake inputs
- [ ] Full end-to-end test: button → LIN → BCM → CAN → LED
- [ ] Fault injection test: unplug LSN node → BCM handles gracefully
- [ ] Long run test: 30 minutes continuous operation without crash

### Jury Defense
- [ ] Can explain every layer and why it exists
- [ ] Can explain LIN frame structure: break, sync, PID, data, checksum
- [ ] Can explain PID parity bit calculation
- [ ] Can explain why RCLK is pulsed after all bits on 74HC595
- [ ] Can explain why active LOW logic is used on shift registers
- [ ] Can explain why threading is needed for dual-bus operation
- [ ] Can explain the state machine pattern and why it is better than if/else chains
- [ ] Can explain why config.py exists and what problem it solves
- [ ] Can explain the known limitation: Linux is not a hard real-time OS

---

## 12. Jury Defense Preparation

These are the questions your jury will most likely ask. Prepare answers for all of them.

### Architecture Questions

**Q: Why did you use a 4-layer architecture?**
Each layer has one responsibility. HAL abstracts hardware, drivers abstract protocols, app contains business logic. This means changing hardware (e.g. different GPIO library) only requires changing HAL — not the application. It also makes testing easier because each layer can be tested independently.

**Q: Why does app/ never import hal/ directly?**
Because app/ should not know what hardware exists. If tomorrow the GPIO library changes, only hal/ changes. App/ is insulated from hardware decisions.

**Q: Why config.py?**
Magic numbers scattered across files are a maintenance nightmare. If the LIN baud rate changes, you would need to find every file that contains 19200. With config.py, you change it in one place.

### Protocol Questions

**Q: What is the difference between LIN and CAN?**
LIN is single-master, single-wire, 19.2kbit/s, low cost, used for body functions. CAN is multi-master, differential 2-wire, up to 1Mbit/s, more robust, used for critical functions. LIN is always polled by master. CAN is event-driven.

**Q: What is a LIN PID and why does it have parity bits?**
PID = Protected ID. It is the 6-bit frame ID with 2 parity bits added (P0 and P1). The parity bits allow the slave to detect transmission errors on the ID byte. P0 = XOR of bits 0,1,2,4. P1 = NOT of XOR of bits 1,3,4,5.

**Q: Why is the LIN schedule 30ms and not faster?**
LIN runs at 19.2kbit/s. One frame (break + sync + PID + 1-5 data bytes + checksum) takes approximately 2-4ms. With 6 slots at 5ms each = 30ms cycle. This gives margin for processing time and Linux timer jitter (±1ms).

### Implementation Questions

**Q: Why threading in main.py?**
The LIN schedule loop blocks for 30ms per cycle. The CAN receive loop blocks waiting for frames. Both must run simultaneously. Threading allows both loops to run concurrently on the same process.

**Q: What is the known limitation of your platform?**
Raspberry Pi runs Linux, which is not a hard real-time OS. The LIN scheduler has timing jitter of ±1-2ms due to OS scheduling. This is acceptable for a didactic platform but not for production vehicles which require hard real-time guarantees (e.g. using AUTOSAR on dedicated MCUs).

**Q: How does your fault handler work?**
On LIN timeout: log error, retry once. On second failure: set fault flag for that node, suspend polling of that node. BCM continues running other nodes normally. This prevents one faulty node from blocking the entire schedule.

---

*Document version: 1.0 | Generated for PFE 2025 | BCM Node Development*
*Next session: Start with config.py → hal/gpio_hal.py → drivers/lin_master.py*
