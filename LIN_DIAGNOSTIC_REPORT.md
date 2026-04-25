# LIN Communication Diagnostic Report
**Date:** 2026-04-24
**Codebase:** BCM / LSN / WBP nodes
**Symptom:** After adding WBP LIN node, LSN stops working (or fails intermittently). WBP also fails. Errors: `Expected 6 bytes, got 0` / `Expected 4 bytes, got 0/1/2`.

---

## Executive Summary

There are **4 real bugs** across 3 files. Two of them are critical and explain 100% of your symptoms. The problems interact with each other, which is why everything fell apart at once when you added WBP.

---

## BUG #1 — CRITICAL | WBP Arduino (`src/main.cpp`)
### SoftwareSerial debug prints disable interrupts and block the hardware UART ISR

**File:** `wbp/WBP_Node/src/main.cpp`, lines 35–38

```cpp
void loop() {
    unsigned long now = millis();
    if (now - last_sample_time >= 250) {
        // ADC sampling only here, correctly gated
    }

    // ❌ These 4 lines run on EVERY loop iteration — no 250ms gate:
    debugSerial.print("W0:"); debugSerial.print(window_states[0]);
    debugSerial.print(" W1:"); debugSerial.print(window_states[1]);
    debugSerial.print(" W2:"); debugSerial.print(window_states[2]);
    debugSerial.print(" W3:"); debugSerial.println(window_states[3]);
}
```

**Why this is fatal:**

`SoftwareSerial` is a pure software implementation. To maintain bit timing accuracy, it **disables global interrupts** for the entire duration of each byte it transmits. Your debug string `"W0:0 W1:0 W2:0 W3:0\n"` is ~20 characters. At 9600 baud, each character takes ~1.04ms. That means:

> **~20ms of interrupt-disabled CPU time, every single loop iteration.**

Your LIN slave is entirely interrupt-driven (`USART_RX_vect` ISR in `lin_slave.cpp`). When SoftwareSerial is transmitting, that ISR **cannot fire**. The hardware UART can still receive bytes into its 1-byte buffer, but:
- If the **BREAK** arrives → stored in UDR0, interrupt pending but blocked.
- If the **SYNC** byte arrives next → UART **overrun error** (OE0), previous byte lost.
- Once interrupts re-enable → ISR fires for the BREAK, state transitions to `WAIT_SYNC`.
- But SYNC is already gone. Nothing comes for 500ms+ → ISR stays stuck in `WAIT_SYNC`.
- BCM master reads 0 bytes after its 50ms wait → **"Expected 4 bytes, got 0"**.

If interrupts are re-enabled mid-header (e.g., between SYNC and PID), you get partial states → **"got 1"** or **"got 2"**.

**The fix:** Move the debug prints inside the 250ms gate, or throttle them with their own counter. They should NOT run every loop iteration.

```cpp
// CORRECT: inside the 250ms gate
if (now - last_sample_time >= 250) {
    last_sample_time = now;
    // ... ADC sampling ...
    debugSerial.print("W0:"); debugSerial.print(window_states[0]);
    // etc.
}
```

---

## BUG #2 — CRITICAL | LSN Python Slave (`lsn/lin_protocol/slave.py`)
### False BREAK detection: LSN misidentifies WBP response data bytes as LIN BREAK signals

**File:** `lsn/lin_protocol/slave.py`, line 55

```python
def _receive_header(self):
    while True:
        # ❌ Reads any 0x00 byte as a BREAK — including data bytes from WBP!
        if self.ser.in_waiting and self.ser.read(1) == bytes([BREAK_BYTE]):
            break
```

**The LIN bus is shared.** When the BCM master requests data from WBP (frame 0x12), WBP sends back 4 data bytes + checksum. Because LIN is a single-wire bus, the LSN Raspberry Pi **also receives those 4 bytes**.

Here is the problem: `BREAK_BYTE = 0x00`, and `WINDOW_OFF = 0` in the WBP enum. When no window switch is pressed (the normal/idle state), `window_states[i] = 0 = 0x00`.

So WBP sends `[0x00, 0x00, 0x00, 0x00, checksum]` most of the time. The LSN slave's BREAK detection loop reads each byte and checks `== 0x00`. It will immediately **trigger a false BREAK** on the first window state byte.

**What happens next (the chain reaction):**

1. BCM sends header for LSN (0x14) → LSN responds correctly with 6 bytes ✓
2. BCM immediately sends header for WBP (0x12) → LSN also receives BREAK+SYNC+PID for 0x12.
3. LSN has no handler for 0x12 → silently ignores it, loops back to `_receive_header()`.
4. WBP sends response: `[0x00, 0x00, 0x00, 0x00, checksum]`.
5. LSN reads first byte `0x00` → **false BREAK detected!**
6. LSN reads second byte `0x00` expecting SYNC → `0x00 != 0x55` → `LINSyncError` → `continue`.
7. LSN has now **consumed 2 bytes** from WBP's response and loops back to BREAK detection.
8. Remaining bytes `[0x00, 0x00, checksum]` are still in the UART buffer.
9. LSN reads the next `0x00` → **another false BREAK!** Reads next as SYNC → another error.
10. Now the LSN slave has stale bytes and corrupt state when the BCM's next real request for 0x14 arrives.
11. Result: LSN does not respond in time → **"Expected 6 bytes, got 0"**.

This is why **LSN started breaking AFTER WBP was added** — before WBP, there were no stray 0x00 data bytes on the bus between polls.

**Why this is hard to distinguish from a BREAK:**

On Linux/pyserial with default termios settings, a genuine LIN BREAK (framing error) is presented as `0x00` in the receive buffer — indistinguishable from a regular data byte of value `0x00`. Proper distinction requires enabling `PARMRK`/`INPCK` termios flags, which mark genuine break conditions with a 3-byte sequence `\xff\x00\x00` instead.

**The fix (short-term):** Register a handler for frame 0x12 on the LSN slave so it correctly "absorbs" the WBP request header without confusion. This won't fix the data byte problem, but will fix the synchronization.

**The fix (proper):** On the LSN Pi, configure the UART with `PARMRK` + `INPCK` so that real framing errors arrive as `\xff\x00\x00` (3-byte sequence) and regular `0x00` data bytes arrive as just `\x00`. Then update `_receive_header()` to look for the 3-byte sequence. This is the only robust solution.

---

## BUG #3 — MEDIUM | BCM LIN Master Driver (`bcm/drivers/lin_master.py`)
### `LINFrameError` is never caught — causes noisy but misleading error messages

**File:** `bcm/drivers/lin_master.py`, lines 13–25

```python
def request_frame(frame_id: int, length: int) -> bytes | None:
    try:
        response = master_instance.request_data(frame_id, expected_data_length=length)
        ...
    except LINChecksumError as e:    # ✓ caught
        ...
    except LINTimeoutError as e:     # ✓ caught
        ...
    # ❌ LINFrameError is NOT caught here!
```

`master.py`'s `request_data()` raises `LINFrameError` when it receives fewer bytes than expected:
```python
if len(data) != expected_data_length:
    raise LINFrameError(f"Expected {expected_data_length} bytes, got {len(data)}")
```

`LINFrameError` is imported in neither the driver nor the exceptions list. It propagates all the way up to `main.py`'s outer `except Exception as e`, which is why you see:
```
ERROR: [LSN] Frame request failed: Expected 6 bytes, got 0
ERROR: [WBP] Frame request failed: Expected 4 bytes, got 0
```

This is the exact error message you reported. The exception is not wrong — the framing did fail — but it should be caught and handled gracefully in the driver layer, not as a generic exception in `main.py`.

**The fix:**
```python
from bcm.lin_protocol.exceptions import LINChecksumError, LINTimeoutError, LINFrameError

def request_frame(frame_id: int, length: int) -> bytes | None:
    try:
        response = master_instance.request_data(frame_id, expected_data_length=length)
        ...
    except LINChecksumError as e:
        logger.error(f"Checksum error for frame ID {hex(frame_id)}: {e}")
        return None
    except LINTimeoutError as e:
        logger.error(f"Timeout error for frame ID {hex(frame_id)}: {e}")
        return None
    except LINFrameError as e:          # ← ADD THIS
        logger.error(f"Frame error for frame ID {hex(frame_id)}: {e}")
        return None
```

---

## BUG #4 — MEDIUM | WBP Arduino (`src/lin_slave.cpp`)
### Blocking while-loops inside ISR stall the entire CPU for ~2.6ms

**File:** `wbp/WBP_Node/src/lin_slave.cpp`, lines 44–52

```cpp
case LINSlaveState::RESPOND:
    for (int i = 0; i < 4; i++) {
        while (!(UCSR0A & (1 << UDRE0)));  // ← Blocking wait inside ISR
        UDR0 = window_states[i];
    }
    while (!(UCSR0A & (1 << UDRE0)));      // ← Another blocking wait
    UDR0 = calculate_checksum(window_states, calculate_pid(WBP_FRAME), 4);
    state = LINSlaveState::WAIT_BREAK;
    break;
```

The `RESPOND` state is triggered from within the `USART_RX_vect` ISR (when it receives the PID byte). At that point, global interrupts are disabled (AVR disables the I-bit when entering any ISR). The blocking `while` loops transmit 5 bytes at 19200 baud:

> 5 bytes × ~0.52ms/byte = **~2.6ms with interrupts disabled**

During this time:
- `millis()` / Timer0 does not advance (Timer0 overflow ISR cannot fire).
- Any other UART byte that arrives during this window goes to the 1-byte hardware buffer and the ISR pending flag. If a second byte arrives before the first is read → **overrun error**.
- SoftwareSerial `debugSerial` cannot send or receive.

For 5 bytes this is usually OK since the BCM master waits 50ms before reading. But combined with Bug #1, it compounds the timing problems. The proper pattern on AVR is to use a transmit buffer + TX Empty interrupt (UDRIE0) for non-blocking ISR transmission.

---

## BCM Timing Analysis (Informational — not a bug, but important context)

Your BCM main loop comment says `# A 20ms sleep ensures we run at ~50Hz`. The actual loop time is much higher:

| Operation | Time |
|---|---|
| Wakeup GPIO pulse (LSN) | 10ms |
| BREAK signal + stabilization (LSN) | ~25ms |
| 50ms wait for LSN response | 50ms |
| Read 6 + 1 bytes (negligible) | ~0ms |
| Wakeup GPIO pulse (WBP) | 10ms |
| BREAK signal + stabilization (WBP) | ~25ms |
| 50ms wait for WBP response | 50ms |
| `time.sleep(0.02)` | 20ms |
| **Total per cycle** | **~190ms** |

Actual loop rate: **~5 Hz**, not 50 Hz. This means buttons feel sluggish (~200ms latency). For a future improvement, the two wakeup pulses could be overlapped, or the 50ms response wait could be reduced since slaves respond in ~2-3ms.

---

## Bug Priority Summary

| # | File | Severity | Effect |
|---|---|---|---|
| 1 | `wbp/WBP_Node/src/main.cpp` | 🔴 CRITICAL | WBP never responds reliably (ISR missed due to SoftwareSerial) |
| 2 | `lsn/lin_protocol/slave.py` | 🔴 CRITICAL | LSN desynchronizes from false BREAK on WBP data bytes |
| 3 | `bcm/drivers/lin_master.py` | 🟡 MEDIUM | `LINFrameError` uncaught, bubbles to main loop |
| 4 | `wbp/WBP_Node/src/lin_slave.cpp` | 🟡 MEDIUM | Blocking TX loops inside ISR, compounds timing |

---

## Fix Order Recommendation

1. **Fix Bug #1 first** (move debug prints inside the 250ms gate in `main.cpp`) — this will immediately fix most WBP failures.
2. **Fix Bug #2 second** (handle frame 0x12 on LSN slave, or use PARMRK BREAK detection) — this will fix LSN desync.
3. **Fix Bug #3** (add `LINFrameError` to the except chain in `lin_master.py`) — clean up error handling.
4. **Fix Bug #4** (refactor ISR RESPOND state to non-blocking TX) — optional but good practice.
