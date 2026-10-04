# Robot Nano Hand: Servo Programming

## What this project is
A learning project for programming The Robot Studio's open-source **Robot Nano Hand**
(robotnanohand.com, github.com/TheRobotStudio/robot-nano-hand). It is a tendon-driven hand
with 4 fingers, a thumb and a wrist: 11 serial bus servos in total. Long-term goals:
- a voice AI agent that poses the hand through function calls
- ASL fingerspelling
- maybe EMG control later

**Teach as you go.** Contributors include Python beginners. Prefer readable code with
comments that explain *why*. Explain the protocol rather than hiding it, and keep each step
small enough to understand. README.md is the getting-started guide for beginners: keep it
accurate when commands, files or setup change.

## Current phase
The servos are **bare on the desk, not mounted in the hand.** The goal is to get comfortable
programming the controller board and servos.

| Step | Status |
|---|---|
| 1. Choose a language | **Done: Python 3.14, managed with uv.** |
| 2. Basic test with raw bytes | **Done.** `servo_first_steps.py` pings, reads, moves and back-drives an SC09 on real hardware (2026-10-04). |
| 3. Choose an SDK | **Leaning towards `ftservo-python-sdk`** (see below), after the raw-bytes exercises. |

## Tooling
- **Python 3.14**, pinned in `.python-version`. 3.15 is too new: torch has no 3.15 wheels
  yet, so lerobot won't install on it. Revisit once torch supports it.
- **uv** manages Python, the virtualenv and dependencies. Use `uv run <script>.py` and
  `uv add <package>`. Don't tell people to activate a venv or use `pip install`.
- Dependencies live in `pyproject.toml`, and `uv.lock` is committed.

## Hardware
| Part | Details |
|---|---|
| Hand servos | Waveshare **SC09** (a rebrand of the Feetech SCS0009, with the same protocol) ×10 for fingers and thumb. Each comes with horns, screws and a 3-port bus connector board. |
| Wrist servo | Feetech **SCS15**, dual-axis |
| Controller | Waveshare **Bus Servo Adapter (A)**: USB-C to a half-duplex TTL serial bus. Our unit has a WCH **CH343** (USB `1a86:55d3`, "USB Single Serial"), not the CH340 some docs mention |
| Power | 6 V 5 A supply into the adapter's 5.5 × 2.1 mm DC jack |
| Host | macOS (Apple Silicon) |

### Hard rules
- **The adapter's jumper must be on B for USB control.** Position A is for UART from a microcontroller.
- **Never supply more than 6 V.** The adapter passes the input voltage straight to the servo bus, and Waveshare rates the SC09 at 4–6 V.
- **Connect both USB and the 6 V supply, and make sure the supply is switched on.** The servos are not powered from USB. The adapter's red LED lights from USB alone, so it is not proof of servo power. With the supply off, pings get garbled bytes back (our own packet, distorted) instead of a reply.
- **Every servo ships as ID 1 at 1,000,000 baud.** Set IDs with **only one servo on the bus at a time**.
- **Before anything that writes to servo EEPROM** (IDs, limits, baud rate), say what it will do and get the user's confirmation first.
- Once servos are in the hand, enforce position limits and a torque limit in software so a stalled grip can't overheat the small gearboxes.

### Planned servo IDs (from step 3 of the build guide)
| IDs | Role |
|---|---|
| Odd IDs 1, 3, 5, 7 | Finger spread (side to side) |
| Even IDs 2, 4, 6, 8 | Finger tendons (curl) |
| 9 | Thumb roll |
| 10 | Thumb tendon |
| 11 | Wrist pitch (SCS15) |

## Protocol notes
Taken from Feetech's official SDK source (`FTServo_Python`, `scscl.py`). Items marked
**✓ hardware** were confirmed on a Waveshare SC09 on 2026-10-04; the rest are unverified.

**Protocol family.** These are Feetech **SCS servos using protocol 1**, not the STS/SMS
series. The register maps differ. In Feetech's SDK, use the `scscl` class, not `sms_sts`.

**Packet format** (✓ hardware). `FF FF | ID | LEN | INSTR | PARAMS… | CHECKSUM`
- `LEN` is the number of params plus 2.
- `CHECKSUM` is `~(ID + LEN + INSTR + sum(PARAMS)) & 0xFF`.
- IDs 0–252 are valid; `0xFE` is broadcast (no reply).

**Instructions.**
| Code | Instruction |
|---|---|
| `0x01` | Ping |
| `0x02` | Read (params: start address, byte count) |
| `0x03` | Write (params: start address, data…) |
| `0x04` / `0x05` | Reg write / action (queue a write, then trigger it) |
| `0x83` | Sync write |
| `0x82` | Sync read: **not supported on protocol 1** (lerobot refuses it), so read servos one at a time |

**Replies** (✓ hardware). `FF FF | ID | LEN | ERROR | DATA… | CHECKSUM`. This adapter does
**not** echo the transmitted packet; `servo_first_steps.py` still skips an exact echo in case
other adapters do. Error bits:
`0x01` voltage, `0x02` angle sensor, `0x04` overheat, `0x08` overcurrent, `0x20` overload.

**Byte order** (✓ hardware). Multi-byte values on SCS servos are **big-endian** (high byte first). The STS
series is the opposite.

**Registers** (from `scscl.py`).
| Address | Register | Notes |
|---|---|---|
| 3 | Model number | 2 bytes, read-only. **1284** on the Waveshare SC09 ✓ hardware |
| 5 | ID | EEPROM |
| 6 | Baud rate | EEPROM, 0 = 1 Mbaud |
| 9 / 11 | Min / max angle limit | 2 bytes each, EEPROM. Writing both as 0 switches to PWM (wheel) mode |
| 40 | Torque enable | ✓ hardware |
| 42 | Goal position | 2 bytes, then 2 bytes of goal time (ms), then 2 bytes of goal speed. Position + speed ✓ hardware |
| 48 | EEPROM lock | Write 0 to unlock before changing EEPROM, then 1 to relock |
| 56 | Present position | 2 bytes ✓ hardware |
| 58 | Present speed | 2 bytes |
| 60 | Present load | 2 bytes |
| 62 | Present voltage | 1 byte, tenths of a volt (61 = 6.1 V) ✓ hardware |
| 63 | Present temperature | 1 byte, °C ✓ hardware |
| 66 | Moving | 1 byte. **Clears early**: read 0 while still ~25 steps from the target. Don't use it to detect arrival |

**Moves** (✓ hardware). Goal time 0 plus a speed works. Speed is roughly **steps per second**:
at 300 the servo covered ~320 steps/s. Positions land within ±2 steps of the target. Wait
`distance / speed + ~0.3 s` before reading back, as `servo_first_steps.py` does.

**Position range.** 0–1023 covers about 300° of travel, and 512 is roughly centre.

**Finding the port on macOS.** The CH343 uses macOS's built-in CDC driver (no install) and
appears as `/dev/cu.usbmodem<serial>`; our adapter is `/dev/cu.usbmodem5B610341031`. A
CH340-based board would appear as `/dev/cu.usbserial-*` or `/dev/cu.wchusbserial*` instead.

## SDK assessment (step 3)
Assessed from source code, not hardware:

| Candidate | Verdict |
|---|---|
| **`ftservo-python-sdk`** (PyPI, from Feetech's `FTServo_Python`) | **Recommended.** Official, maintained (2.0.1, Sept 2026), has the `scscl` class with correct byte order. Method names mirror the protocol, so not much is hidden. |
| `feetech-servo-sdk` (PyPI, third-party, 2022) | Avoid. No `scscl` class, and it defaults to little-endian, so SCS values come back byte-swapped unless you call `SCS_SETEND(1)`. |
| Waveshare's ST/SC library | Not yet checked. Probably a repackaging of Feetech's SDK. |
| lerobot's Feetech motor bus | Supports `scs0009` (its HopeJR hand uses it). Heavy (torch), and hides a lot. Useful later for teleoperation and learning. |

**Package conflict:** `ftservo-python-sdk` and `feetech-servo-sdk` both install a module named
`scservo_sdk`, and lerobot depends on the old one. Keep lerobot work in a separate project or
environment.

## Next exercises
1. Change the move speed and range.
2. Assign IDs one servo at a time (EEPROM write: confirm first).
3. Chain two servos.
4. Use sync write to move several servos at once.
5. Rewrite the basic test with `ftservo-python-sdk` and compare.
6. Check the SCS15 wrist servo's voltage rating before powering it.

## Working style
- Explain hardware and protocol concepts; keep explanations friendly to beginners.
- Keep experiments as small, separate scripts until a structure is clearly needed.
- Check docs and source rather than relying on memory, and say when something is unverified.
