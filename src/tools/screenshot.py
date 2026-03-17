#!/usr/bin/env python3
"""
Capture Apple II display as a PNG screenshot from the headless emulator.

Usage:
    python3 -m tools.screenshot -o boot.png
    python3 -m tools.screenshot -c 'PRINT "HELLO WORLD"' -o hello.png
    python3 -m tools.screenshot -c 'HGR:HPLOT 0,0 TO 279,191' -o line.png
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any

from display_bitmap import BitmapDisplay, render_hires_page, write_png
from headless import HeadlessKeyboard, boot_to_prompt
from runtime import Runtime


def capture_hires(mem: Any, page: int = 1, output: str = "screenshot.png") -> None:
    """Capture a HiRes page from memory to PNG.

    Args:
        mem: ObservableMemory (or any indexable) with HiRes data.
        page: HiRes page (1 or 2).
        output: Output PNG file path.
    """
    pixels, w, h = render_hires_page(mem, page)
    write_png(pixels, w, h, output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Apple II screen as PNG")
    parser.add_argument(
        "-o", "--output", default="screenshot.png", help="Output PNG file path (default: screenshot.png)"
    )
    parser.add_argument("-c", "--command", action="append", help="BASIC command to run (can be repeated)")
    parser.add_argument("-n", "--steps", type=int, default=1000000, help="Max steps (instructions) per command (default: 1000000)")
    parser.add_argument("-R", "--rom", default=None, help="ROM file (default: bin/A2SOFT2.BIN)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show progress on stderr")
    args = parser.parse_args()

    rom_path = args.rom
    if rom_path is None:
        rom_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "bin", "A2SOFT2.BIN")

    opts = argparse.Namespace(
        rom=rom_path, ram=None,
        disk=None, disk2=None,
        throttle=False, controller=None,
    )
    runtime = Runtime(opts)

    display = BitmapDisplay(runtime.bus)
    keyboard = HeadlessKeyboard(runtime.bus)
    cpu = runtime.cpu

    if args.verbose:
        print("Booting Apple II...", file=sys.stderr)

    start = time.time()
    boot_steps = boot_to_prompt(cpu, display)

    if not display.has_prompt():
        print("ERROR: Failed to boot to prompt", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"Booted in {boot_steps} steps ({time.time()-start:.1f}s)", file=sys.stderr)

    if args.command:
        for cmd in args.command:
            if args.verbose:
                print(f"Typing: {cmd}", file=sys.stderr)

            keyboard.type_string(cmd)
            initial_prompts = display.count_prompts()

            exec_steps = 0
            while exec_steps < args.steps:
                cpu.step()
                exec_steps += 1
                if exec_steps % 1000 == 0:
                    if display.count_prompts() > initial_prompts:
                        for _ in range(1000):
                            cpu.step()
                        break

            if args.verbose:
                print(f"  Executed {exec_steps} steps", file=sys.stderr)

    display.save_png(args.output)

    if args.verbose:
        print(f"Saved: {args.output}", file=sys.stderr)
        print(file=sys.stderr)
        print("--- Screen Text ---", file=sys.stderr)
        print(display.get_text(), file=sys.stderr)
    else:
        print(args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
