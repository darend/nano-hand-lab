# Nano Hand Lab

Learning to program the servos of [The Robot Studio](https://www.therobotstudio.com/)'s open-source
**Robot Nano Hand** ([robotnanohand.com](https://robotnanohand.com),
[GitHub](https://github.com/TheRobotStudio/robot-nano-hand)): a tendon-driven hand
with 4 fingers, a thumb and a wrist, moved by 11 small servo motors.

Right now the servos are loose on the desk. The goal is to learn how to talk to them
before they go into the hand.

**Contents:** [What you need](#what-you-need) ·
[Terminal basics](#terminal-basics) · [Getting started](#getting-started) ·
[Every time you come back](#every-time-you-come-back) · [Editing code](#editing-code) ·
[Playing in Python](#playing-in-python) · [How the servos talk](#how-the-servos-talk) ·
[What's in the script](#whats-in-the-script) · [Things to try](#things-to-try) ·
[Troubleshooting](#troubleshooting) · [Words you'll see](#words-youll-see)

## What you need

| Part | What it does |
|---|---|
| Waveshare **SC09** servos (or Feetech SCS0009) | The motors. Each one has its own ID number and a little computer inside. |
| Waveshare **Bus Servo Adapter (A)** | Plugs into the Mac over USB-C and talks to the servos over one shared wire (the "bus"). |
| **6 V** power supply (5 A) | Powers the servos. USB alone is not enough. |
| A Mac | Runs the Python code. |

## Terminal basics

You'll type commands into **Terminal**, a text window for talking to the Mac.

- **Open it:** press **⌘ Space**, type `Terminal`, press **Return**.
- **Run a command:** type it (or paste it with **⌘ V**) and press **Return**.
- **Stop a running program:** press **Control C** (the `control` key, not ⌘).
- **Run the last command again:** press **↑**, then **Return**.
- **Fill in a long name:** type the first few letters and press **Tab**.
- **Where am I?** `pwd` shows the folder you're in. `ls` lists what's in it.
  `cd folder-name` moves into a folder. `cd ..` moves back out. `cd ~` goes home.

In this guide, grey boxes are commands to type. Type them one line at a time.

## Getting started

You only do these steps once.

### 1. Install uv

[uv](https://docs.astral.sh/uv/) installs Python and everything this project needs. In
Terminal, paste:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Quit Terminal (⌘ Q) and open it again** so it finds `uv`. Check it worked:

```
uv --version
```

You should see something like `uv 0.12.23`. If you see `command not found`, quit and reopen
Terminal again.

### 2. Get the code

```
cd ~
git clone https://github.com/darend/nano-hand-lab.git
cd nano-hand-lab
```

This makes a folder called `nano-hand-lab` in your home folder.

If a box pops up asking to install **"command line developer tools"**, click **Install**, wait
for it to finish, then run the `git clone` line again.

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
2. Plug in the 6 V supply **and switch it on at the wall**. The adapter's red light comes on
   from USB alone, so it doesn't tell you the servos have power.
3. Plug the adapter into the Mac with USB-C. If the Mac asks **"Allow accessory to
   connect?"**, click **Allow**.

### 4. Find the adapter's port

The "port" is the name the Mac gives the adapter.

```
ls /dev/cu.*
```

Look for one starting `/dev/cu.usbmodem`. Our adapter shows up as:

```
/dev/cu.usbmodem5B610341031
```

The number comes from the adapter's serial number, so a different adapter has a different
name. This guide uses ours in its examples: swap in yours if it's different. No driver is
needed.

If you only see `Bluetooth-Incoming-Port` and `debug-console`, unplug the adapter, plug it
back in and try again. Still nothing? Try another USB-C cable: some cables only carry power,
not data.

### 5. Run the first script

Use the port name from step 4:

```
uv run servo_first_steps.py /dev/cu.usbmodem5B610341031
```

The first run takes a little longer while uv downloads Python. Then the script:

1. **Pings** the servo to check it's there.
2. **Reads** its model number and position.
3. **Moves** it to 512 → 400 → 624 → 512.
4. **Switches torque off** so you can turn the horn by hand and watch the position change.
   Press **Control C** to stop.

It prints every message it sends (`->`) and every reply (`<-`) as hex bytes:

```
1. Ping servo 1
  -> FF FF 01 02 01 FB
  <- FF FF 01 02 00 FC
   It answered!
```

Add `--quiet` to hide the bytes, or `--id 3` to talk to a servo with a different ID:

```
uv run servo_first_steps.py /dev/cu.usbmodem5B610341031 --quiet
```

## Every time you come back

1. Wire it up again (jumper on **B**, 6 V, USB).
2. Open Terminal and go to the project folder:
   ```
   cd ~/nano-hand-lab
   ```
3. Get any updates:
   ```
   git pull
   ```
4. Run things with `uv run`.

If `git pull` complains that your changes would be overwritten, you edited a file that also
changed online. See [Editing code](#editing-code) for how to avoid that.

## Editing code

Use a code editor, not TextEdit. **[Visual Studio Code](https://code.visualstudio.com/)** is
free and good:

1. Download it, drag it to **Applications** and open it.
2. **File → Open Folder…** and choose `nano-hand-lab` in your home folder.
3. When it suggests the **Python** extension, click **Install**.
4. **View → Terminal** opens a Terminal inside the editor, already in the right folder. You
   can run `uv run ...` there.

**Make your own copy to experiment with.** Then `git pull` never clashes with your changes:

```
cp servo_first_steps.py my_test.py
uv run my_test.py /dev/cu.usbmodem5B610341031
```

Save with **⌘ S** before you run it. If you break something, you still have the original.

**When Python shows an error,** read the **last line** first: it says what went wrong. The
lines above it show which line of your file it happened on.

## Playing in Python

Instead of running the whole script, you can send commands one at a time and see what
happens. Start Python inside the project:

```
uv run python
```

The prompt changes to `>>>`. Type these one at a time (use your port name):

```python
from servo_first_steps import *
ser = serial.Serial("/dev/cu.usbmodem5B610341031", BAUD, timeout=0.05)

ping(ser, 1)
read_position(ser, 1)
set_torque(ser, 1, True)
move_to(ser, 1, 300)
move_to(ser, 1, 700, speed=100)
read_register(ser, 1, 63, 1)     # temperature: [22] means 22 °C
set_torque(ser, 1, False)

ser.close()
exit()
```

`from servo_first_steps import *` borrows all the functions from the script.
`build_packet(1, PING)` shows a packet without sending it.

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

The servo replies with the same shape, except the instruction byte is replaced by an
**error** byte. `00` means everything is fine.

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

### Worked example: reading the position

To ask servo 1 for 2 bytes starting at register 56 (`38` in hex):

```
FF FF  01  04  02  38 02  BE
       ID  LEN READ addr count  checksum
```

- `LEN` is 4: two parameters (`38`, `02`) plus 2.
- Checksum: 01 + 04 + 02 + 38 + 02 = 41 (hex). Flip the bits of 41 → BE.

The reply might be:

```
FF FF  01  04  00   01 F4   05
       ID  LEN err  data    checksum
```

The error byte is `00` (fine) and the data is `01 F4` = 1 × 256 + 244 = **500**.

## What's in the script

[`servo_first_steps.py`](servo_first_steps.py) is in sections, top to bottom:

| Section | What it does |
|---|---|
| **Protocol constants** | Names for the numbers: `PING = 0x01`, `REG_PRESENT_POSITION = 56`, and so on. |
| **Packet building** | `build_packet` puts the bytes in the right order and adds the checksum. |
| **Talking on the bus** | `transact` sends a packet and reads the reply. `ping`, `read_register` and `write_register` use it. |
| **Friendly helpers** | `read_position`, `set_torque` and `move_to`: the ones you'll use most. |
| **The experiment** | `main` runs steps 1–4. Change this part to try your own moves. |

## Things to try

1. **Check a checksum by hand.** For the ping `FF FF 01 02 01 FB`: 01 + 02 + 01 = 04, and
   flipping the bits of 04 gives FB.
2. **Change the moves.** In your copy, edit the list `(512, 400, 624, 512)` in `main`, or the
   `speed = 300` line just above it. Speed is roughly steps per second. What's the fastest
   speed that still looks smooth?
3. **Read the temperature and voltage.** Registers 63 and 62, one byte each. Voltage is in
   tenths of a volt, so `61` means 6.1 V. Temperature is in °C. Does it go up after the servo
   has been working for a while?
4. **Wave.** Write a loop that moves between two positions five times.
5. **Give servos their own IDs**, one servo at a time. *(Script coming. This changes the
   servo's permanent memory, so ask before you run it.)*
6. **Chain two servos** with different IDs and move them both.
7. **Move several servos at once** with the sync-write instruction (`83`).

## Troubleshooting

| What you see | What to check |
|---|---|
| `command not found: uv` | Quit Terminal (⌘ Q) and reopen it. If it still happens, redo [step 1](#1-install-uv). |
| `No such file or directory: servo_first_steps.py` | You're in the wrong folder. Run `cd ~/nano-hand-lab`. |
| `could not open port` | Wrong port name: run `ls /dev/cu.*` again. Or another program (or another Terminal window) has the port open: close it. |
| `no reply: is the 6 V supply switched on?` | Check the supply is plugged in **and switched on at the wall**: the red light on the adapter only means USB is connected. Then: is the jumper on **B**? Is the servo plugged in firmly? Is the ID right? |
| `bad checksum` | Loose cable, or two servos with the same ID on the bus. |
| `!! servo reports error` | It tells you what: voltage, overheat, overload... Unplug the power and let it rest. |
| The servo replies but doesn't move | Is torque on? Is the position you asked for different from where it is now? |
| The servo buzzes or feels hot | Something is stopping it reaching its position. Turn torque off and check nothing is in the way. |

## Words you'll see

| Word | Meaning |
|---|---|
| **Servo** | A motor with a sensor and a tiny computer, so it can move to an exact position and hold it. |
| **Horn** | The plastic arm or disc that screws onto the servo's shaft. |
| **Bus** | One shared set of wires that every servo plugs into. Each servo listens for its own ID. |
| **Torque** | Twisting force. Torque on = the servo holds its position. Torque off = it goes limp. |
| **Register** | A numbered slot in the servo's memory, like a cell in a spreadsheet. |
| **EEPROM** | The part of the servo's memory that's kept when the power is off, like its ID. |
| **Hex** | Numbers in base 16, written with 0–9 and A–F. `FF` = 255, `38` = 56. Every byte is two hex digits. |
| **Baud** | How fast bytes travel on the bus. These servos use 1,000,000 bits per second. |
| **Packet** | One complete message on the bus, from `FF FF` to the checksum. |
| **Checksum** | A number added to the end of a packet so the receiver can spot scrambled bytes. |

## Servo ID plan

From step 3 of the Robot Nano Hand build guide:

| IDs | Job |
|---|---|
| 1, 3, 5, 7 | Finger spread (side to side) |
| 2, 4, 6, 8 | Finger curl (pull the tendon) |
| 9 | Thumb roll |
| 10 | Thumb tendon |
| 11 | Wrist pitch (SCS15 servo) |

## License

The code in this repo is released under the [MIT License](LICENSE). The Robot Nano Hand design
itself belongs to The Robot Studio; see [their repo](https://github.com/TheRobotStudio/robot-nano-hand)
for its license.
