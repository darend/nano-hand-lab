#!/usr/bin/env python3
"""
First steps with a Feetech SCS servo (Waveshare SC09 / SCS0009), using raw bytes.

No SDK on purpose: every packet is built by hand here so you can see exactly
what goes down the wire. Run it with the port of the Bus Servo Adapter (A):

    uv run servo_first_steps.py /dev/cu.usbmodem5B610341031
    uv run servo_first_steps.py /dev/cu.usbmodem5B610341031 --id 3 --quiet

(Your port name will be different: run `ls /dev/cu.*` to find it.)

What it does:
  1. Ping the servo                      (is anyone there?)
  2. Read its model number and position  (READ instruction)
  3. Move 512 -> 400 -> 624 -> 512        (WRITE instruction)
  4. Torque off, then stream the position while you turn the horn by hand

Before running: jumper on B, 6 V supply plugged in AND switched on, USB plugged
in, one servo on the bus.
"""

import argparse
import sys
import time

import serial  # pyserial, listed in pyproject.toml

# ---------------------------------------------------------------------------
# Protocol constants
# ---------------------------------------------------------------------------

BAUD = 1_000_000  # every servo ships at 1 Mbaud

# Instruction codes: the 5th byte of every packet we send.
PING = 0x01
READ = 0x02
WRITE = 0x03

# Register addresses (SCS series "memory table"). Each servo is basically a
# tiny block of memory; you control it by reading and writing these addresses.
REG_MODEL = 3             # 2 bytes, read-only. SCS0009 should report 1284.
REG_ID = 5                # 1 byte, EEPROM (survives power-off)
REG_TORQUE_ENABLE = 40    # 1 byte: 1 = hold position, 0 = limp
REG_GOAL_POSITION = 42    # 2 bytes position, then 2 bytes time, then 2 bytes speed
REG_PRESENT_POSITION = 56 # 2 bytes, read-only

# Bits in the ERROR byte of a reply. Non-zero means the servo is unhappy.
ERROR_BITS = {
    0x01: "input voltage",
    0x02: "angle sensor",
    0x04: "overheat",
    0x08: "overcurrent",
    0x20: "overload",
}

VERBOSE = True  # print every packet in hex; turned off with --quiet


# ---------------------------------------------------------------------------
# Packet building
# ---------------------------------------------------------------------------

def checksum(body):
    """Sum everything after the FF FF header, keep the low byte, flip all bits.

    The servo does the same sum on what it receives; if one bit got
    corrupted on the wire, the checksums won't match and it ignores the packet.
    """
    return ~sum(body) & 0xFF


def build_packet(servo_id, instruction, params=()):
    """FF FF | ID | LEN | INSTR | PARAMS... | CHECKSUM

    LEN counts the bytes that follow it: the instruction, the params and the
    checksum, so it's len(params) + 2.
    """
    body = [servo_id, len(params) + 2, instruction, *params]
    return bytes([0xFF, 0xFF, *body, checksum(body)])


def to_bytes16(value):
    """SCS servos are big-endian: high byte first. (STS servos are the opposite!)"""
    return [(value >> 8) & 0xFF, value & 0xFF]


def from_bytes16(hi, lo):
    return (hi << 8) | lo


def hexdump(data):
    return " ".join(f"{b:02X}" for b in data)


# ---------------------------------------------------------------------------
# Talking on the bus
# ---------------------------------------------------------------------------

def read_packet(ser):
    """Read one reply: FF FF | ID | LEN | ERROR | DATA... | CHECKSUM.

    Returns the raw bytes, or None if nothing arrived before the timeout.
    """
    # Hunt for the FF FF header. Anything before it is line noise.
    prev = None
    while True:
        b = ser.read(1)
        if not b:
            return None
        if prev == 0xFF and b[0] == 0xFF:
            break
        prev = b[0]

    head = ser.read(2)  # ID, LEN
    if len(head) < 2:
        return None
    rest = ser.read(head[1])  # LEN bytes: ERROR/INSTR, DATA/PARAMS, CHECKSUM
    if len(rest) < head[1]:
        return None
    return bytes([0xFF, 0xFF]) + head + rest


def transact(ser, packet):
    """Send a packet and return (error_byte, data_bytes) from the reply.

    The bus is half-duplex: one wire carries both directions, so we talk,
    then stop and listen. Some adapters hear their own transmission and hand
    it back to us (an "echo"); if the first thing we read is exactly what we
    sent, we skip it.
    """
    ser.reset_input_buffer()  # throw away stale bytes from earlier exchanges
    ser.write(packet)
    if VERBOSE:
        print(f"  -> {hexdump(packet)}")

    reply = read_packet(ser)
    if reply == packet:
        if VERBOSE:
            print("  (echo of our own packet, skipping)")
        reply = read_packet(ser)

    if reply is None:
        raise TimeoutError("no reply: is the 6 V supply switched on? "
                           "Then check the jumper is on B, the servo cable, and the servo ID")
    if VERBOSE:
        print(f"  <- {hexdump(reply)}")

    if checksum(reply[2:-1]) != reply[-1]:
        raise IOError(f"bad checksum in reply {hexdump(reply)}")

    error = reply[4]
    if error:
        problems = [name for bit, name in ERROR_BITS.items() if error & bit]
        print(f"  !! servo reports error 0x{error:02X}: {', '.join(problems) or 'unknown'}")
    return error, reply[5:-1]


def ping(ser, servo_id):
    transact(ser, build_packet(servo_id, PING))


def read_register(ser, servo_id, address, length):
    """READ params are: start address, how many bytes.

    Returns the bytes as a list of numbers, e.g. [22] or [2, 0].
    """
    _, data = transact(ser, build_packet(servo_id, READ, [address, length]))
    return list(data)


def write_register(ser, servo_id, address, values):
    """WRITE params are: start address, then the bytes to write there."""
    transact(ser, build_packet(servo_id, WRITE, [address, *values]))


# ---------------------------------------------------------------------------
# Friendly helpers built on the three primitives above
# ---------------------------------------------------------------------------

def read_position(ser, servo_id):
    hi, lo = read_register(ser, servo_id, REG_PRESENT_POSITION, 2)
    return from_bytes16(hi, lo)


def set_torque(ser, servo_id, on):
    write_register(ser, servo_id, REG_TORQUE_ENABLE, [1 if on else 0])


def move_to(ser, servo_id, position, speed=300):
    """Write 6 bytes starting at 42: goal position, goal time, goal speed.

    Following Feetech's own example, we leave time at 0 and set a speed.
    Speed is roughly in steps per second: at 300, a move of 300 steps takes
    about a second. Position is 0-1023 over roughly 300 degrees, so 512 is
    about the middle.
    """
    position = max(0, min(1023, position))
    write_register(ser, servo_id, REG_GOAL_POSITION,
                   to_bytes16(position) + to_bytes16(0) + to_bytes16(speed))


# ---------------------------------------------------------------------------
# The experiment
# ---------------------------------------------------------------------------

def main():
    global VERBOSE

    parser = argparse.ArgumentParser(description="Talk to one SCS servo with raw packets.")
    parser.add_argument("port", help="e.g. /dev/cu.usbserial-1410 (run: ls /dev/cu.*)")
    parser.add_argument("--id", type=int, default=1, help="servo ID (factory default is 1)")
    parser.add_argument("--quiet", action="store_true", help="don't print raw packets")
    args = parser.parse_args()
    VERBOSE = not args.quiet
    sid = args.id

    # timeout=0.05: if the servo hasn't answered within 50 ms it isn't going to.
    with serial.Serial(args.port, BAUD, timeout=0.05) as ser:
        print(f"\n1. Ping servo {sid}")
        ping(ser, sid)
        print("   It answered!")

        print("\n2. Read model number and position")
        model = from_bytes16(*read_register(ser, sid, REG_MODEL, 2))
        print(f"   Model number: {model}  (SCS0009 is expected to be 1284)")
        print(f"   Position: {read_position(ser, sid)}")

        print("\n3. Move it")
        set_torque(ser, sid, True)
        speed = 300
        for target in (512, 400, 624, 512):
            start = read_position(ser, sid)
            print(f"   -> {target}")
            move_to(ser, sid, target, speed)
            # Wait long enough to arrive: distance / speed, plus a little extra.
            # (Register 66 "moving" goes to 0 slightly before it arrives, so we
            # don't rely on it.)
            time.sleep(abs(target - start) / speed + 0.3)
            print(f"   now at {read_position(ser, sid)}")

        print("\n4. Torque off. Turn the horn by hand (Ctrl-C to stop)")
        set_torque(ser, sid, False)
        VERBOSE = False  # 20 packets a second is too much to read
        try:
            while True:
                pos = read_position(ser, sid)
                bar = "#" * (pos * 50 // 1023)
                print(f"\r   {pos:4d} |{bar:<50}|", end="", flush=True)
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n   Done.")


if __name__ == "__main__":
    try:
        main()
    except (TimeoutError, IOError, serial.SerialException) as e:
        sys.exit(f"\nError: {e}")
