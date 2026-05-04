# Codebase Issues Report — Automotive Didactic Platform
**Generated:** 2026-04-30
**Scope:** Full project (WBP, BCM, LSN) — Cycle 2 post-WBP integration
**Author:** Code Review (Supervisor Pass)

---

## How to Read This Report

Issues are sorted by severity: **BLOCKING → SIGNIFICANT → MINOR**.
Each entry contains:
- **File & Location** — exact file and line(s) affected
- **What is wrong** — precise description of the defect
- **Why it matters** — the underlying concept and consequence
- **How to fix it** — concrete guidance (conceptual, not implemented code)

---

# PART 1 — BLOCKING ISSUES
> These must be resolved before any jury defense or live demo. They either crash the system, produce wrong output, or make the test suite non-functional.

---

## BLOCKING-1 — Hardcoded Windows absolute paths in `bcm/config.py`

**File:** `bcm/config.py`, lines 1–2
**Status:** Carried over from Cycle 1. Not fixed.

```python
LDF_path = "C:\\Users\\Omar\\Documents\\ME\\PFE 2026\\KPIT\\Code\\didactic_code\\LDF.ldf"
DBC_path = "C:\\Users\\Omar\\Documents\\ME\\PFE 2026\\KPIT\\Code\\didactic_code\\BCM_CAN.dbc"
```

**What is wrong:**
The paths to the LDF and DBC files are Windows absolute paths. The BCM runs on a Raspberry Pi (Linux). This code crashes immediately on the target hardware with a `FileNotFoundError`.

**Why it matters:**
Configuration that contains environment-specific values (paths, IPs, port names) must be derived at runtime relative to the project root, not hardcoded to a developer's local machine. This is a deployment hygiene principle.

**How to fix it:**
Replace both paths with runtime-relative construction using `os.path`:
```python
import os
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LDF_path = os.path.join(_PROJECT_ROOT, 'LDF.ldf')
DBC_path = os.path.join(_PROJECT_ROOT, 'BCM_CAN.dbc')
```
This resolves correctly on any machine regardless of where the project is cloned.

---

## BLOCKING-2 — `lsn/lin_protocol/slave.py` false BREAK detection on WBP data bytes

**File:** `lsn/lin_protocol/slave.py`, line 55
**Status:** Documented in `LIN_DIAGNOSTIC_REPORT.md` as BUG #2. Not fixed.

```python
while True:
    if self.ser.in_waiting and self.ser.read(1) == bytes([BREAK_BYTE]):
        break
```

**What is wrong:**
`BREAK_BYTE = 0x00`. When WBP is idle (all windows off), it sends `[0x00, 0x00, 0x00, 0x00, checksum]` over the shared LIN bus. The LSN slave is also on this bus and receives those bytes. Its BREAK detection loop reads each byte and checks `== 0x00`. The first WBP window state byte (value 0x00) triggers a false BREAK. The LSN then reads the next byte expecting SYNC (0x55) but gets another 0x00 → `LINSyncError` → `continue`. The LSN has now consumed WBP response bytes, is in an inconsistent state, and fails to respond to the BCM's next legitimate request for frame 0x14.

**Why it matters:**
On a hardware UART (like the ATmega328P in WBP), a LIN break is a *framing error* — a physical electrical condition detectable via the `FE0` flag in `UCSR0A`. On Linux with pyserial default `termios` settings, a framing error and a data byte of value `0x00` are presented identically in the receive buffer. The two are indistinguishable without additional termios configuration. Using `0x00` as a BREAK sentinel is architecturally incorrect for a shared bus.

**How to fix it (short-term — workable for demo):**
Register a dummy handler for frame ID 0x12 in the LSN slave so it absorbs the WBP request header without entering an error state. This does not solve the data-byte problem but eliminates the worst-case desync.

**How to fix it (proper):**
Configure the LSN UART with `PARMRK` and `INPCK` termios flags before opening the serial port. With these flags, a genuine framing error (LIN break) is delivered as the 3-byte sequence `\xff\x00\x00`, while a regular data byte of value `0x00` is delivered as just `\x00`. Update `_receive_header()` to detect the 3-byte sequence instead of a single `0x00`.

```python
import termios, fcntl
# After opening the serial port:
attrs = termios.tcgetattr(ser.fd)
attrs[0] |= termios.INPCK | termios.PARMRK   # enable parity/framing error marking
attrs[0] &= ~termios.IGNPAR                  # do not ignore parity errors
termios.tcsetattr(ser.fd, termios.TCSANOW, attrs)
```
Then in `_receive_header()`, read 1 byte and check if it equals `b'\xff'` to signal the start of the 3-byte break sequence, then read 2 more bytes to confirm.

---

## BLOCKING-3 — `test_gateway.py` calls `process_and_send()` with wrong number of arguments

**File:** `bcm/test_gateway.py`, lines 25, 31, 36, 43
**Status:** Carried over from Cycle 1. Not fixed.

```python
bytes_out = gw.process_and_send(null_payload, flash_state=False)
```

**What is wrong:**
`process_and_send()` now has the signature `process_and_send(self, lsn_lin_data, wbp_lin_data, flash_state)` — three positional arguments. The test file still calls it with two arguments (the old API). Every test call in this file raises a `TypeError` at runtime. The entire test suite is non-functional.

**Why it matters:**
Broken tests are worse than no tests. They give a false sense of coverage while providing no actual validation. An interviewer who runs your test file will see it crash immediately.

**How to fix it:**
Add a dummy `wbp_payload` argument to every `process_and_send()` call in the test file:
```python
dummy_wbp = b'\x00\x00\x00\x00'
bytes_out = gw.process_and_send(null_payload, dummy_wbp, flash_state=False)
```
After fixing the call signature, also add test cases that exercise the WBP path: one with all windows OFF, one with window 0 UP, one with window 1 DOWN.

---

## BLOCKING-4 — LDF bit collision: `Right_Turn_Btn` and `Rear_Fog_Btn` both at bit position 29

**File:** `LDF.ldf`, lines 33 and 38
**Status:** Carried over from Cycle 1. Not fixed.

```
Right_Turn_Btn,  29 ;   /* byte 3, bit 5 */
Rear_Fog_Btn,    29 ;   /* ⚠ currently same as Right_Turn in gateway.py */
```

**What is wrong:**
Two different signals share the same bit position in the frame. This is a collision. One overwrites the other. Any LDF tooling (ldfparser, Vector CANdb++, LIN Explorer) will reject this LDF as structurally invalid. Furthermore, `gateway.py`'s bit parsing for `right_btn` and `rear_fog_sw` must diverge from the LDF to work at all — the specification and implementation are inconsistent.

**Why it matters:**
The LDF is the authoritative source of truth for your LIN network. If the LDF is wrong, every downstream tool and every node that implements the LDF is unreliable. This also blocks your project from being validated with any standard automotive toolchain.

**How to fix it:**
Decide the correct bit position for each signal by tracing it to the physical 74HC165 shift register layout. Assign each signal a unique bit position in the frame. Verify that `gateway.py`'s bit parsing matches the corrected LDF. Document the mapping in a comment block explaining which 74HC165 pin maps to which byte and bit.

---

## BLOCKING-5 — Blocking `while` loops inside `USART_RX_vect` ISR

**File:** `wbp/WBP_Node/src/lin_slave.cpp`, lines 44–49
**Status:** Carried over from Cycle 1. Not fixed.

```cpp
case LINSlaveState::WAIT_PID:
    if (received_byte == calculate_pid(WBP_FRAME)) {
        uint8_t pid = calculate_pid(WBP_FRAME);
        for (int i = 0; i < 4; i++) {
            while (!(UCSR0A & (1 << UDRE0)));  // ← blocking wait in ISR
            UDR0 = window_states[i];
        }
        while (!(UCSR0A & (1 << UDRE0)));      // ← blocking wait in ISR
        UDR0 = calculate_checksum(window_states, pid, 4);
    }
```

**What is wrong:**
These `while` loops spin inside the `USART_RX_vect` interrupt service routine waiting for the UART data register to be empty. On AVR, entering any ISR clears the global interrupt enable bit (I-bit in SREG). This means that while these loops execute, no other interrupt can fire. Transmitting 5 bytes at 19200 baud takes approximately 2.6ms with interrupts disabled. During this time: Timer0 does not advance (so `millis()` drifts), any byte that arrives in the UART is held in the 1-byte hardware buffer and will be lost if a second byte arrives before the ISR returns.

**Why it matters:**
ISRs are meant to be fast and non-blocking. The cardinal rule is: do the minimum work in the ISR (load data into a buffer, set a flag) and let the main loop do the heavy lifting. Blocking inside an ISR is one of the most common and severe embedded programming errors. In an interview, this is an instant red flag.

**How to fix it (conceptual):**
Use the UART Data Register Empty interrupt (`UDRIE0`) for non-blocking transmission:
1. In `WAIT_PID`, when the correct PID is received, load the first byte into a TX ring buffer and enable `UDRIE0` (set `UDRE0` bit in `UCSR0B`).
2. In a separate `USART_UDRE_vect` ISR, write the next byte from the buffer to `UDR0`. When the buffer is empty, disable `UDRIE0`.
3. The transmission happens asynchronously — the `USART_RX_vect` returns immediately without blocking.

---

## BLOCKING-6 — WBP window commands computed but never used

**File:** `bcm/app/gateway.py`, lines 108–109
**Status:** New finding in Cycle 2.

```python
window_commands = self.decode_wbp_frame(wbp_lin_data)
logger.info(f"[WBP] Window commands: {window_commands}")
# ← window_commands is never read again after this line
```

**What is wrong:**
The BCM receives WBP LIN frames, decodes them into a list of window commands, and then discards the result. There is no Window State Machine, no `WINDOW_CMD` CAN message, and no `WINDOW_STATUS` output. The "integration" ends at logging. The BCM knows what the window buttons say but does nothing about it.

**Why it matters:**
The stated goal is to integrate WBP into the BCM. The receive path and the decode path are implemented. The act path — the part that actually controls windows — is completely missing. This is the next major implementation task.

**What needs to be built (not yet implemented, but must exist for a complete demo):**

1. **`WindowSM` (Window State Machine)** — equivalent to `TurnSignalSM`. States: `IDLE`, `MOVING_UP`, `MOVING_DOWN`, `AUTO_UP`, `AUTO_DOWN`, `FAULT`. Transition logic: command UP → MOVING_UP, button released → IDLE, WBP timeout → FAULT.

2. **`WINDOW_CMD` CAN message in `BCM_CAN.dbc`** — a new message (e.g., ID `0x103`) with 4 signals (one per window), each 2 bits wide: `0=STOP`, `1=UP`, `2=DOWN`, `3=RESERVED`. BCM sends this to the CAN bus after processing WBP input.

3. **WBP status byte in the LIN frame** — the WBP currently sends 4 bytes (raw states). A 5th byte carrying node health and fault flags would allow the BCM to distinguish "button released" from "hardware fault." Update the Arduino, LDF (`wbp, 5`), and `BCM_PAYLOAD_LEN`.

4. **WBP diagnostic poll** — add `WBP_DIAG_FRAME_ID = 0x3D` to `main.py` and poll it alongside the LSN diagnostic. Even if the Arduino does not yet respond, the infrastructure should exist.

---

# PART 2 — SIGNIFICANT ISSUES
> These do not crash the system but represent real engineering defects — correctness risks, protocol violations, or patterns that would fail a production code review.

---

## SIG-1 — `flash_timer.py` uses `time.time()` instead of `time.monotonic()`

**File:** `bcm/app/flash_timer.py`, lines 17 and 21

```python
self.last_toggle_time = time.time()
...
current_time = time.time()
```

**What is wrong:**
`time.time()` returns wall-clock time, which is not guaranteed to be monotonic. NTP (Network Time Protocol), which runs on Raspberry Pi by default, can adjust the system clock both forward and backward. If the clock jumps backward by 0.5 seconds, the flash timer will stall for 0.5 seconds. If it jumps forward, the timer fires immediately.

**How to fix it:**
Replace both occurrences with `time.monotonic()`. It is guaranteed to only increase, is unaffected by NTP, and is the correct choice for any elapsed-time measurement.

---

## SIG-2 — PID computed twice inside ISR (`lin_slave.cpp`)

**File:** `wbp/WBP_Node/src/lin_slave.cpp`, lines 41 and 43

```cpp
if (received_byte == calculate_pid(WBP_FRAME)) {   // first call
    uint8_t pid = calculate_pid(WBP_FRAME);         // second call — redundant
```

**What is wrong:**
`calculate_pid()` is called once in the condition check, and immediately called again to assign to `pid`. At the point of assignment, `received_byte` has already been validated to equal `calculate_pid(WBP_FRAME)` — it IS the PID. Using `received_byte` directly eliminates the second function call.

**Why it matters:**
Calling a function with arithmetic operations inside an ISR is wasteful and increases the ISR's execution time. Every microsecond inside an ISR is time during which other interrupts cannot be serviced.

**How to fix it:**
Replace `uint8_t pid = calculate_pid(WBP_FRAME);` with `uint8_t pid = received_byte;`. The value is identical — the check on the previous line guarantees this.

---

## SIG-3 — `cli()/sei()` around 4 `analogRead()` calls creates ~400µs interrupt blackout

**File:** `wbp/WBP_Node/src/main.cpp`, lines 106–111

```cpp
cli();
for (int i = 0; i < 4; i++) {
    int adc_val = analogRead(ADC_PINS[i]);
    ...
}
sei();
```

**What is wrong:**
Each `analogRead()` takes ~104µs on ATmega328P at 16MHz. Four calls = ~416µs with global interrupts disabled. At 19200 baud, one LIN byte arrives every ~521µs. A 400µs interrupt blackout means a LIN byte arriving during ADC sampling may be buffered but the ISR cannot fire. If a second byte arrives before the ISR drains the first, an UART overrun error (OE0) occurs and the first byte is lost.

**How to fix it:**
Use a double-buffer pattern: sample all 4 ADC channels into a local array inside `cli()/sei()`, then copy only the final results to `window_states[]`. The critical section should only cover the copy (4 single-byte writes), not the ADC conversions themselves. Better still, run ADC conversions with interrupts enabled, then disable interrupts only for the atomic copy.

---

## SIG-4 — `_wakeup_slave()` called before every LIN frame

**File:** `bcm/lin_protocol/master.py`, lines 57 and 71

```python
def send_command(self, frame_id, data):
    self._wakeup_slave()   # ← fires every frame
    self.send_break()
    ...

def request_data(self, frame_id, expected_data_length=8):
    self._wakeup_slave()   # ← fires every frame
    self.send_break()
    ...
```

**What is wrong:**
The LIN wakeup signal is specified in LIN 2.x for waking slave nodes from low-power (sleep) mode. It is not a per-frame handshake. WBP and LSN are never put to sleep, so this wakeup pulse adds ~12ms of unnecessary GPIO overhead per frame (2ms pulse + 10ms `time.sleep`). With two nodes polled per cycle, this adds ~24ms of dead time every loop iteration.

**How to fix it:**
Remove `_wakeup_slave()` from `send_command()` and `request_data()`. Keep the method available to call once during bus initialization or when a slave is detected as unresponsive. Per the LIN 2.x spec, wakeup should only be sent when transitioning the bus from sleep to active state.

---

## SIG-5 — `can_payload[::-1]` kludge in `gateway.py`

**File:** `bcm/app/gateway.py`, line 207

```python
can_payload = can_payload[::-1]
```

**What is wrong:**
The CAN payload is reversed here to compensate for a `reversed()` call in the LSN's output driver. Both sides are doing a reversal to cancel each other out. The root cause — a byte-order mismatch between the DBC signal layout and the LSN's shift register bit-feeding order — is not fixed; it is hidden by two equal and opposite hacks. If either side's reversal is removed independently, the LED mapping breaks.

**Why it matters:**
This is a bilateral protocol kludge. The DBC says the signals are in a specific byte order. The code sends them in a different order and relies on both ends agreeing to flip. This cannot be validated by any external tool — you cannot send the CAN frame through a standard analyser and get correct signal values.

**How to fix it:**
Determine the correct byte order that the 74HC595 chain physically requires. Update the DBC signal bit positions to match that physical layout directly. Remove the reversal from both `gateway.py` and the LSN driver. The canonical fix requires tracing the shift register daisy-chain topology and updating the DBC to reflect it accurately.

---

## SIG-6 — LIN break detection in `lsn/lin_protocol/slave.py` uses `0x00` byte match

*(See BLOCKING-2 above for full detail — this issue is also listed here because it has a secondary copy in `bcm/lin_protocol/slave.py`.)*

**File:** `bcm/lin_protocol/slave.py`, line 55 — identical bug, different file

**Additional finding:** `bcm/lin_protocol/slave.py` is dead code. The BCM is a LIN master, not a slave. `LINSlave` is never imported or used in any BCM module. This file should be deleted. It contains the same 0x00 BREAK detection bug, and its presence is misleading.

---

## SIG-7 — `RESPOND` state declared in enum but never used

**File:** `wbp/WBP_Node/include/lin_slave.h`, line 14

```cpp
enum class LINSlaveState {
    WAIT_BREAK,
    WAIT_SYNC,
    WAIT_PID,
    RESPOND    // ← never transitioned into
};
```

**What is wrong:**
The state machine has 4 declared states but only 3 are ever used. The response is transmitted inline inside the `WAIT_PID` case handler. `RESPOND` is never the target of any state transition. A reader will search for `case LINSlaveState::RESPOND:` and find nothing.

**How to fix it:**
Either remove `RESPOND` from the enum (simplest), or refactor the WAIT_PID handler to transition into RESPOND and handle the transmission there — which would also be the right place to remove the blocking while-loops (see BLOCKING-5).

---

## SIG-8 — `bcm/main.py` hardcodes serial port string instead of using config constant

**File:** `bcm/main.py`, line 51

```python
init_lin_master('/dev/serial0')
```

**What is wrong:**
`bcm/lin_protocol/constants.py` already defines `DEFAULT_SERIAL_PORT = '/dev/serial0'`. This constant is ignored. The port is hardcoded as a string literal in `main.py`.

**How to fix it:**
Import the constant and pass it: `init_lin_master(DEFAULT_SERIAL_PORT)`. Better still, add `LIN_SERIAL_PORT = '/dev/serial0'` to `bcm/config.py` alongside `LIN_BAUDRATE`, and import it from there in `main.py`.

---

## SIG-9 — LDF `WBP_Frame` schedule entry missing `ms` unit suffix

**File:** `LDF.ldf`, line 72

```
WBP_Frame delay 5.0;         ← no unit
LSN_Input_Frame delay 5.0 ms ;  ← correct
```

**What is wrong:**
LDF grammar requires a time unit suffix on all `delay` values. `WBP_Frame delay 5.0` without `ms` is a syntax error. Any LDF parser (`ldfparser` Python package, Vector LIN Explorer, CANalyzer) will reject the entire schedule table section.

**How to fix it:**
Change to `WBP_Frame delay 5.0 ms ;` — add `ms` before the semicolon.

---

## SIG-10 — Non-deterministic BCM loop timing: actual rate ~5Hz, documented as ~50Hz

**File:** `bcm/main.py` (loop) and `Documentation/Next_Steps.md`

**What is wrong:**
The `time.sleep(0.002)` at the end of the loop implies ~2ms overhead per iteration, targeting ~500Hz. The actual per-cycle cost (from `LIN_DIAGNOSTIC_REPORT.md`) is ~190ms:

| Operation | Time |
|---|---|
| Wakeup pulse × 2 nodes | ~20ms |
| BREAK generation × 2 nodes | ~50ms |
| Response wait × 2 nodes | ~100ms |
| `time.sleep(0.002)` | 2ms |
| **Total** | **~172–190ms** |

Actual loop rate is **~5 Hz**, not 50 Hz. The `time.sleep(0.002)` is misleading — it implies the developer believes the loop runs fast when it does not.

**How to fix it:**
Remove `time.sleep(0.002)` or replace it with a documented rate comment. The primary improvement is eliminating the per-frame `_wakeup_slave()` calls (~24ms saved) and reducing the `request_data()` deadline from 100ms to 20ms (responses arrive in ~2–3ms). These two changes alone would bring the loop to ~30–40ms (~25–33 Hz), which is more defensible.

---

## SIG-11 — CRC-8 function duplicated across 3 files

**Files:** `bcm/app/gateway.py`, `lsn/lsn_node/app/output_module.py`, `lsn/lsn_node/tests/bcm_fault_injector.py`
**Status:** Carried over from Cycle 1. Not fixed.

**What is wrong:**
The same `_calculate_crc8()` function (SAE J1850, polynomial 0x1D, init 0xFF) is copy-pasted in three places. If a bug is found in the algorithm, it must be fixed in three places. If a developer updates one copy, the other two diverge silently.

**How to fix it:**
Create a shared utility module, e.g., `shared/e2e_utils.py` or `bcm/utils/crc.py`, and import from it in all three places.

---

## SIG-12 — No input debounce anywhere in the system

**Files:** `wbp/WBP_Node/src/main.cpp` (ADC), `lsn/lsn_node/app/input_module.py` (74HC165)
**Status:** Carried over from Cycle 1. Not fixed.

**What is wrong:**
ADC samples are taken once per millisecond with no averaging or hysteresis. The 74HC165 shift register is read once per LIN poll with no consistency check. Physical buttons have contact bounce lasting 1–20ms. A single noisy sample can produce false state transitions.

**Why it matters:**
Any state machine fed by unbounced inputs is unreliable. In an interview, "how do you debounce inputs?" is a basic embedded question. The answer in your code is currently "I don't."

**How to fix it (ADC):**
For the resistor-ladder ADC, implement hysteresis: maintain a `previous_state` and only transition to a new state if the ADC value has been in the new region for N consecutive samples (N=3–5 is typical at 1ms sampling).

**How to fix it (digital):**
For the 74HC165 buttons, read the register twice with a short delay and only accept the reading if both reads agree.

---

# PART 3 — MINOR ISSUES
> These are style, consistency, and hygiene issues. They do not affect runtime correctness but affect code quality, readability, and professional presentation.

---

## MIN-1 — `windowState::UNKNOWN` declared but never returned

**File:** `wbp/WBP_Node/include/window_swich.h`, line 10

The `UNKNOWN` member exists in the `windowState` enum but `window_swich()` returns one of the other four states for all ADC ranges. Dead enum member misleads readers.

**Fix:** Remove `UNKNOWN` from the enum, or add an explicit `UNKNOWN` return for ADC values above all defined thresholds (as a hardware fault indicator — see BLOCKING-6 discussion on missing fault detection).

---

## MIN-2 — ADC threshold constants are magic numbers with no derivation

**File:** `wbp/WBP_Node/include/window_swich.h`, lines 13–16

```cpp
const uint16_t B_UP_AUTO  = 145;
const uint16_t B_UP       = 245;
const uint16_t B_DOWN_AUTO = 310;
const uint16_t B_DOWN     = 402;
```

No comment explains which resistors produce these ADC values, what the reference voltage is, or what the tolerance margins are. These are not self-documenting.

**Fix:** Add a comment block above the constants:
```cpp
// Resistor ladder on A0–A3 (VCC=5V, ADC full-scale=1023, R_pull=10kΩ)
// Button positions and their mid-point ADC values: ...
// Thresholds are set at the midpoint between adjacent ladder levels.
```

---

## MIN-3 — `pinMode(13, OUTPUT)` called inside `loop()` instead of `setup()`

**File:** `wbp/WBP_Node/src/main.cpp`, line 131

```cpp
void loop() {
    ...
    pinMode(13, OUTPUT);   // ← should be in setup()
    digitalWrite(13, any_active ? HIGH : LOW);
}
```

`pinMode()` configures a hardware register. Calling it on every loop iteration is wasteful and implies the developer does not know that pin mode persists between loop iterations.

**Fix:** Move `pinMode(13, OUTPUT)` to `setup()`.

---

## MIN-4 — `int` parameter type instead of `uint16_t` for 10-bit ADC value

**File:** `wbp/WBP_Node/include/window_swich.h`, line 19

```cpp
windowState window_swich(int adc_value);
```

The ATmega328P ADC is 10-bit and returns values 0–1023. The semantically correct type is `uint16_t`. Using `int` allows negative values to be passed without a compiler warning.

**Fix:** Change the parameter type to `uint16_t`.

---

## MIN-5 — Inconsistent header guard style in WBP

**Files:** `lin_slave.h` (uses `#ifndef/#define/#endif`), `window_swich.h` (uses `#pragma once`)

Both styles work, but mixing them within the same project is inconsistent. Pick one and apply it uniformly.

---

## MIN-6 — Unused frame type constants in `bcm/lin_protocol/constants.py`

**File:** `bcm/lin_protocol/constants.py`, lines 12–14

```python
UNCONDITIONAL_FRAME = 0
EVENT_TRIGGERED_FRAME = 1
SPORADIC_FRAME = 2
```

These constants are defined but never referenced in any file. Dead code.

**Fix:** Remove them, or use them where frame type information is relevant (e.g., annotate `request_data()` and `send_command()` with which frame type they implement).

---

## MIN-7 — `headlightSM` class name violates PascalCase

**File:** `bcm/app/headlight_sm.py`, line 5

```python
class headlightSM:
```

All other state machine classes use PascalCase (`TurnSignalSM`, `BrakeSignalSM`, `ReverseSignalSM`). This one starts lowercase. Python convention (PEP-8) requires class names to use CapWords.

**Fix:** Rename to `HeadlightSM`. Update all import sites.

---

## MIN-8 — `.pio/build/` artifacts committed to git

**File:** `wbp/WBP_Node/.gitignore` and repo root
**Status:** Carried over from Cycle 1. Not fixed.

Compiled firmware artifacts (`.o` files, `.elf`, `.hex`, `.a` libraries) are tracked in git. These are build outputs — they should be generated, not versioned.

**Fix:** Add to `.gitignore`:
```
.pio/build/
.pio/libdeps/
```
Then run `git rm -r --cached wbp/WBP_Node/.pio/build/` to untrack the existing files.

---

## MIN-9 — `bcm-node.service` runs as root user

**File:** `bcm/bcm-node.service`

Running the BCM Python process as root gives it unrestricted access to the filesystem and kernel interfaces. This violates the principle of least privilege.

**Fix:** Create a dedicated system user (e.g., `bcm-node`) and assign it to the `dialout` group (for serial port access) and `gpio` group (for GPIO access). Set `User=bcm-node` and `Group=bcm-node` in the service file.

---

## MIN-10 — Typo in function and file name: `window_swich` should be `window_switch`

**Files:** `wbp/WBP_Node/src/window_swich.cpp`, `wbp/WBP_Node/include/window_swich.h`

The word "switch" is misspelled as "swich" throughout — in the filename, the function name, and all call sites. This is visible in every include and every function call.

**Fix:** Rename the file to `window_switch.cpp` / `window_switch.h`, rename the function to `window_switch()`, and update all call sites. A trivial find-and-replace.

---

# PART 4 — WHAT IS MISSING FROM THE WBP FRAME

This section answers the specific question: *"Is the WBP frame missing status, diagnostics, or fault detection?"*

**Short answer: Yes — all three are missing.**

### Currently in the WBP LIN frame: 4 bytes, raw button states only.

| Byte | Content |
|---|---|
| Byte 0 | `Window1_State` (0=OFF, 1=DOWN, 2=UP, 3=UP_AUTO, 4=DOWN_AUTO) |
| Byte 1 | `Window2_State` |
| Byte 2 | `Window3_State` |
| Byte 3 | `Window4_State` |

### What a production node would additionally carry:

**Missing — Node status byte (Byte 4):**
A 5th byte indicating WBP node health. Proposed layout:
```
Bits [1:0] = NodeState: 0=INIT, 1=RUNNING, 2=FAULT, 3=RECOVERY
Bit  [2]   = ADC_Fault: 1 if any ADC channel reads outside all defined windows
             (i.e., resistor path open or shorted — hardware fault)
Bit  [3]   = MultiPress_Fault: 1 if two conflicting states detected simultaneously
Bits [7:4] = CommErrorCount: rolling count of consecutive LIN errors (0–15)
```
Without this, the BCM cannot distinguish "all windows idle" (every byte = 0x00) from "WBP hardware dead" (also every byte = 0x00).

**Missing — ADC fault detection on the WBP side:**
`window_swich()` returns `WINDOW_OFF` for all ADC values ≥ 402. An open-circuit resistor ladder (hardware fault) also produces ADC ≈ 1023, which maps to `WINDOW_OFF`. The WBP has no way to signal "I cannot read this channel." Adding a check `if adc_value > THRESHOLD_MAX (e.g., 900) → return WINDOW_FAULT` would allow the status byte to set ADC_Fault.

**Missing — WBP watchdog on the BCM side:**
The BCM logs a warning when WBP fails to respond but takes no further action. There is no:
- Consecutive failure counter
- Latching `WBP_FAULT` flag that gates further window commands
- Recovery attempt (retry logic)
- Diagnostic code logged to a fault table

Compare this to the LSN, which has a full `NodeState` FSM (INIT/RUNNING/FAULT/RECOVERY) and a watchdog counter in `config.py`. WBP needs the equivalent treatment in the BCM processing layer.

**Missing — LIN diagnostic response (0x3D) for WBP:**
The BCM polls the LSN at `0x3D` for health status every 50 cycles. There is no equivalent poll for WBP. The Arduino would need a diagnostic frame handler that returns a status byte. The BCM `main.py` would need a `WBP_DIAG_FRAME_ID = 0x3D` poll (or a separate WBP-specific diagnostic ID).

**Missing — `WINDOW_CMD` CAN message:**
No CAN message exists for windows. After the BCM processes WBP input, it should publish a `WINDOW_CMD` frame (or equivalent) on the CAN bus. This message would carry the 4 window commands and would be received by a power window actuator node (WPA) — which is listed in the LDF Nodes section but not yet implemented.

**Missing — AUTO mode behavior:**
`decode_wbp_frame()` collapses `UP_AUTO` and `UP` to the same output value, and same for `DOWN_AUTO` and `DOWN`. The AUTO flag — which the hardware explicitly communicates — is silently discarded. In a real window controller, AUTO means "run to full travel limit without the driver holding the button." The Window State Machine must treat AUTO as a distinct state that self-sustains until a limit switch or reversal command is received.

---

# SUMMARY TABLE

| ID | File | Severity | Status | One-line description |
|---|---|---|---|---|
| BLOCKING-1 | `bcm/config.py:1-2` | 🔴 BLOCKING | Not fixed | Windows absolute paths crash on RPi |
| BLOCKING-2 | `lsn/lin_protocol/slave.py:55` | 🔴 BLOCKING | Not fixed | 0x00 BREAK detection desyncs LSN on WBP data |
| BLOCKING-3 | `bcm/test_gateway.py:25,31,36,43` | 🔴 BLOCKING | Not fixed | Tests call process_and_send() with wrong arg count |
| BLOCKING-4 | `LDF.ldf:33,38` | 🔴 BLOCKING | Not fixed | Right_Turn and Rear_Fog share bit position 29 |
| BLOCKING-5 | `wbp/src/lin_slave.cpp:44-49` | 🔴 BLOCKING | Not fixed | Blocking while-loops inside ISR |
| BLOCKING-6 | `bcm/app/gateway.py:108-109` | 🔴 BLOCKING | Not fixed | WBP window commands computed, never used |
| SIG-1 | `bcm/app/flash_timer.py:17,21` | 🟠 SIGNIFICANT | New | `time.time()` not monotonic — NTP sensitive |
| SIG-2 | `wbp/src/lin_slave.cpp:43` | 🟠 SIGNIFICANT | New | PID computed twice inside ISR |
| SIG-3 | `wbp/src/main.cpp:106-111` | 🟠 SIGNIFICANT | New | 400µs interrupt blackout during ADC reads |
| SIG-4 | `bcm/lin_protocol/master.py:57,71` | 🟠 SIGNIFICANT | Not fixed | `_wakeup_slave()` fired on every LIN frame |
| SIG-5 | `bcm/app/gateway.py:207` | 🟠 SIGNIFICANT | Not fixed | `can_payload[::-1]` bilateral byte-order kludge |
| SIG-6 | `bcm/lin_protocol/slave.py:55` | 🟠 SIGNIFICANT | New | Dead file with BREAK bug — should be deleted |
| SIG-7 | `wbp/include/lin_slave.h:14` | 🟠 SIGNIFICANT | New | `RESPOND` state declared but never used |
| SIG-8 | `bcm/main.py:51` | 🟠 SIGNIFICANT | New | Serial port hardcoded, config constant ignored |
| SIG-9 | `LDF.ldf:72` | 🟠 SIGNIFICANT | New | WBP_Frame delay missing `ms` unit — syntax error |
| SIG-10 | `bcm/main.py` (loop) | 🟠 SIGNIFICANT | Not fixed | Loop runs at ~5Hz, not documented ~50Hz |
| SIG-11 | `gateway.py` + 2 files | 🟠 SIGNIFICANT | Not fixed | CRC-8 duplicated in 3 files |
| SIG-12 | `main.cpp`, `input_module.py` | 🟠 SIGNIFICANT | Not fixed | No debounce on any input |
| MIN-1 | `window_swich.h:10` | 🟡 MINOR | New | `UNKNOWN` enum value declared, never returned |
| MIN-2 | `window_swich.h:13-16` | 🟡 MINOR | New | ADC threshold magic numbers, no derivation |
| MIN-3 | `main.cpp:131` | 🟡 MINOR | New | `pinMode(13)` inside `loop()` |
| MIN-4 | `window_swich.h:19` | 🟡 MINOR | New | `int` instead of `uint16_t` for ADC value |
| MIN-5 | WBP headers | 🟡 MINOR | New | Inconsistent header guard style |
| MIN-6 | `bcm/lin_protocol/constants.py:12-14` | 🟡 MINOR | New | Unused frame type constants |
| MIN-7 | `bcm/app/headlight_sm.py:5` | 🟡 MINOR | Not fixed | `headlightSM` violates PascalCase |
| MIN-8 | `.gitignore` | 🟡 MINOR | Not fixed | `.pio/build/` artifacts in git |
| MIN-9 | `bcm/bcm-node.service` | 🟡 MINOR | Not fixed | Service runs as root |
| MIN-10 | `window_swich.cpp/.h` | 🟡 MINOR | New | Typo: `swich` should be `switch` |

---

*End of report. Total issues: 6 BLOCKING, 12 SIGNIFICANT, 10 MINOR.*
