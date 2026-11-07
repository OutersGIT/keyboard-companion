#!/usr/bin/env python3
"""Linux raw-HID diagnostic for custom A4 firmware; does not flash firmware.

No GUI or hidapi dependency. Default: listen for pushed reports only.
--pull also sends the custom read-only getter (firmware must implement A4).
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import select
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from keeb_assistant.hid_reader import KC_GET_BATTERY, REPORT_SIZE, _parse_report


def discover(root=Path('/sys/bus/hid/devices')):
    for device in sorted(root.glob('*:3434:*')):
        try:
            descriptor = (device / 'report_descriptor').read_bytes()
            if bytes.fromhex('06 60 ff 09 61') not in descriptor:
                continue
            for node in (device / 'hidraw').glob('hidraw*'):
                yield '/dev/' + node.name
        except OSError:
            continue


def capture(seconds, pull=False):
    opened = []
    try:
        for path in discover():
            try:
                fd = os.open(path, (os.O_RDWR if pull else os.O_RDONLY) | os.O_NONBLOCK)
                opened.append((fd, path))
                if pull:
                    request = bytes([0, KC_GET_BATTERY]) + bytes(REPORT_SIZE - 1)
                    if os.write(fd, request) != len(request):
                        raise OSError('Short HID write')
            except OSError as error:
                print(f'{path}: {error}', file=sys.stderr)
        if not opened:
            print('No accessible Keychron raw-HID interface; check connection and device permissions.', file=sys.stderr)
            return 1
        deadline = time.monotonic() + seconds
        count = 0
        while opened and time.monotonic() < deadline:
            ready, _, _ = select.select([fd for fd, _ in opened], [], [], max(0, deadline-time.monotonic()))
            for fd in ready:
                path = next(path for item, path in opened if item == fd)
                try:
                    packet = os.read(fd, REPORT_SIZE + 1)
                except OSError as error:
                    print(f'{path}: {error}', file=sys.stderr)
                    packet = b''
                if not packet:
                    os.close(fd)
                    opened = [(item, name) for item, name in opened if item != fd]
                    continue
                reading = _parse_report(packet)
                if reading is not None:
                    print(json.dumps({**asdict(reading), 'path': path}), flush=True)
                    count += 1
        return 0 if count else 1
    finally:
        for fd, _ in opened:
            os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=8)
    parser.add_argument('--pull', action='store_true')
    args = parser.parse_args()
    if not 0 < args.seconds <= 30:
        parser.error('--seconds must be greater than 0 and at most 30')
    return capture(args.seconds, args.pull)


if __name__ == '__main__':
    raise SystemExit(main())
