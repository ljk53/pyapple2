from __future__ import annotations

import argparse
import os


def get_options() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apple ][ emulator in Python")
    parser.add_argument("-R", "--rom", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "A2SOFT2.BIN"), help="ROM file to use")
    parser.add_argument("-r", "--ram", help="RAM file to load")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode, no sounds")
    parser.add_argument("-c", "--cassette", help="Cassette wav file to load")
    parser.add_argument("-C", "--controller", default=6502, type=int, help="HTTP controller port")
    parser.add_argument("-K", "--keylog", help="Keyboard strike log file to replay")
    parser.add_argument("-T", "--throttle", action="store_true", help="Throttle CPU to real Apple II speed (1.023 MHz)")
    parser.add_argument("-d", "--disk", help="Disk image (.dsk/.po) to insert in drive 1")
    parser.add_argument("--disk2", help="Disk image (.dsk/.po) to insert in drive 2")
    parser.add_argument("--screenshot", help="Save screenshot to file after N frames and exit (mock only)")
    parser.add_argument("--screenshot-frames", type=int, default=60, help="Number of frames to run before taking screenshot (default: 60)")
    return parser.parse_args()
