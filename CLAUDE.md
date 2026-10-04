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
| 2. Basic test with raw bytes | `servo_first_steps.py` written and packets checked against Feetech's SDK. **Not yet run on hardware.** |
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
| Controller | Waveshare **Bus Servo Adapter (A)**: USB-C to a half-duplex TTL serial bus, with a CH340 USB-serial chip |
| Power | 6 V 5 A supply into the adapter's 5.5 × 2.1 mm DC jack |
| Host | macOS (Apple Silicon) |

### Hard rules
- **The adapter's jumper must be on B for USB control.** Position A is for UART from a microcontroller.
- **Never supply more than 6 V.** The adapter passes the input voltage straight to the servo bus, and Waveshare rates the SC09 at 4–6 V.
- **Connect both USB and the 6 V supply.** The servos are not powered from USB.
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
**Checked against Feetech's official SDK source (`FTServo_Python`, `scscl.py`) but not yet
on hardware.** Update this section once confirmed on a real servo.

**Protocol family.** These are Feetech **SCS servos using protocol 1**, not the STS/SMS
series. The register maps differ. In Feetech's SDK, use the `scscl` class, not `sms_sts`.

**Packet format.** `FF FF | ID | LEN | INSTR | PARAMS… | CHECKSUM`
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

**Replies.** `FF FF | ID | LEN | ERROR | DATA… | CHECKSUM`. Some setups echo the transmitted
packet back; `servo_first_steps.py` skips an exact echo if one arrives. Error bits:
`0x01` voltage, `0x02` angle sensor, `0x04` overheat, `0x08` overcurrent, `0x20` overload.

**Byte order.** Multi-byte values on SCS servos are **big-endian** (high byte first). The STS
series is the opposite.

**Registers** (from `scscl.py`).
| Address | Register | Notes |
|---|---|---|
| 3 | Model number | 2 bytes, read-only. lerobot lists the SCS0009 as 1284 (unconfirmed for the Waveshare SC09) |
| 5 | ID | EEPROM |
| 6 | Baud rate | EEPROM, 0 = 1 Mbaud |
| 9 / 11 | Min / max angle limit | 2 bytes each, EEPROM. Writing both as 0 switches to PWM (wheel) mode |
| 40 | Torque enable | |
| 42 | Goal position | 2 bytes, then 2 bytes of goal time (ms), then 2 bytes of goal speed |
| 48 | EEPROM lock | Write 0 to unlock before changing EEPROM, then 1 to relock |
| 56 | Present position | 2 bytes |
| 58 | Present speed | 2 bytes |
| 60 | Present load | 2 bytes |
| 62 | Present voltage | 1 byte |
| 63 | Present temperature | 1 byte |
| 66 | Moving | 1 byte |

**Moves.** Feetech's example sets goal time to 0 and a speed (e.g. 1500), sleeping roughly
`distance / speed` seconds, which suggests speed is in steps per second. Unverified.

**Position range.** 0–1023 covers about 300° of travel, and 512 is roughly centre.

**Finding the port on macOS.** `/dev/cu.usbserial-*` or `/dev/cu.wchusbserial*` (run
`ls /dev/cu.*`). The CH340 is driver-free on recent macOS; otherwise install WCH's
`CH34XSER_MAC` driver.

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
1. Run `servo_first_steps.py` on hardware and update the protocol notes with what's confirmed.
2. Change the move speed and range.
3. Assign IDs one servo at a time (EEPROM write: confirm first).
4. Chain two servos.
5. Use sync write to move several servos at once.
6. Rewrite the basic test with `ftservo-python-sdk` and compare.

## Working style
- Explain hardware and protocol concepts; keep explanations friendly to beginners.
- Keep experiments as small, separate scripts until a structure is clearly needed.
- Check docs and source rather than relying on memory, and say when something is unverified.
