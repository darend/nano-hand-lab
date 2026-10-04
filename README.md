# Nano Hand Lab

Learning to program the servos of [The Robot Studio](https://www.therobotstudio.com/)'s open-source
**Robot Nano Hand** ([robotnanohand.com](https://robotnanohand.com),
[GitHub](https://github.com/TheRobotStudio/robot-nano-hand)): a tendon-driven hand
with 4 fingers, a thumb and a wrist, moved by 11 small servo motors.

Right now the servos are loose on the desk. The goal is to learn how to talk to them
before they go into the hand.

## What you need

| Part | What it does |
|---|---|
| Waveshare **SC09** servos (or Feetech SCS0009) | The motors. Each one has its own ID number and a little computer inside. |
| Waveshare **Bus Servo Adapter (A)** | Plugs into the Mac over USB-C and talks to the servos over one shared wire (the "bus"). |
| **6 V** power supply (5 A) | Powers the servos. USB alone is not enough. |
| A Mac | Runs the Python code. |

## Getting started

### 1. Install uv (once)

[uv](https://docs.astral.sh/uv/) installs Python and everything this project needs. Open
**Terminal** and paste:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close Terminal and open it again so it finds `uv`. Check it worked:

```
uv --version
```

### 2. Get the code

```
git clone https://github.com/darend/nano-hand-lab.git
cd nano-hand-lab
```

You don't need to install Python yourself. The first time you run something, uv downloads
the right version (3.14) and the libraries listed in `pyproject.toml`.

### 3. Wire it up

> ⚠️ **Read these first.** Getting them wrong can damage the servos.
>
> - **Never use more than 6 V.** The adapter sends the supply voltage straight to the servos.
> - **The jumper on the adapter must be on B** (USB control), not A.
> - **Plug in both USB and the 6 V supply.** The servos don't get power from USB.
> - **Start with one servo on the bus.** They all come from the factory with ID 1, so two new
>   servos on the bus at once will talk over each other.

1. Plug one servo into the adapter.
2. Plug in the 6 V supply.
3. Plug the adapter into the Mac with USB-C.

### 4. Find the adapter's port

```
ls /dev/cu.*
```

Look for something like `/dev/cu.usbserial-1410` or `/dev/cu.wchusbserial1410`. That's the
adapter. If you only see `Bluetooth-Incoming-Port` and `debug-console`, check the USB cable.
If it still doesn't appear, install the
[WCH CH34x driver](https://www.wch-ic.com/downloads/CH34XSER_MAC_ZIP.html).

### 5. Run the first script

Use your own port name from step 4:

```
uv run servo_first_steps.py /dev/cu.usbserial-1410
```

The script:

1. **Pings** the servo to check it's there.
2. **Reads** its model number and position.
3. **Moves** it to 512 → 400 → 624 → 512.
4. **Switches torque off** so you can turn the horn by hand and watch the position change.
   Press **Ctrl-C** to stop.

It prints every message it sends (`->`) and every reply (`<-`) as hex bytes:

```
1. Ping servo 1
  -> FF FF 01 02 01 FB
  <- FF FF 01 02 00 FC
   It answered!
```

Add `--quiet` to hide the bytes, or `--id 3` to talk to a servo with a different ID.

## How the servos talk

Every message on the bus is a short **packet** of bytes:

```
FF FF | ID | LEN | INSTRUCTION | PARAMETERS... | CHECKSUM
```

| Part | Meaning |
|---|---|
| `FF FF` | "A packet starts here." |
| `ID` | Which servo the packet is for (0–252; `FE` means "every servo"). |
| `LEN` | How many bytes come after this one: the parameters plus 2. |
| `INSTRUCTION` | What to do: `01` ping, `02` read, `03` write. |
| `PARAMETERS` | For read and write: which **register** (memory address) to use, then the data. |
| `CHECKSUM` | Add up everything after `FF FF`, keep the last byte, flip all the bits. The servo does the same sum to check nothing got scrambled. |

Each servo has a small table of memory **registers**. You control it by writing to them and
check on it by reading them:

| Address | Register | Size |
|---|---|---|
| 5 | ID | 1 byte |
| 40 | Torque on (1) / off (0) | 1 byte |
| 42 | Goal position, then goal time, then goal speed | 2 + 2 + 2 bytes |
| 56 | Present position | 2 bytes |
| 62 | Voltage | 1 byte |
| 63 | Temperature | 1 byte |

Positions go from **0 to 1023** over about 300°, so **512 is the middle**. Two-byte values are
sent **high byte first**: 400 is `01 90` because 1 × 256 + 0x90 (144) = 400.

## Things to try

1. **Check a checksum by hand.** For the ping `FF FF 01 02 01 FB`: 01 + 02 + 01 = 04, and
   flipping the bits of 04 gives FB.
2. **Change the moves.** Edit the list `(512, 400, 624, 512)` in step 3 of the script, or the
   `speed=300` in `move_to`.
3. **Read the temperature.** Register 63, one byte: `read_register(ser, sid, 63, 1)`.
4. **Give servos their own IDs**, one servo at a time. *(Script coming. This writes to the
   servo's permanent memory, so ask before you run it.)*
5. **Chain two servos** with different IDs and move them both.
6. **Move several servos at once** with the sync-write instruction (`83`).

## Troubleshooting

| What you see | What to check |
|---|---|
| `no reply: check power...` | Is the 6 V supply on? Is the jumper on **B**? Is the servo plugged in firmly? Is the ID right? |
| `could not open port` | Wrong port name; run `ls /dev/cu.*` again. Or another program has the port open. |
| `bad checksum` | Loose cable, or two servos with the same ID on the bus. |
| `!! servo reports error` | It tells you what: voltage, overheat, overload... Unplug the power and let it rest. |

## Servo ID plan

From step 3 of the Robot Nano Hand build guide:

| IDs | Job |
|---|---|
| 1, 3, 5, 7 | Finger spread (side to side) |
| 2, 4, 6, 8 | Finger curl (pull the tendon) |
| 9 | Thumb roll |
| 10 | Thumb tendon |
| 11 | Wrist pitch (SCS15 servo) |
