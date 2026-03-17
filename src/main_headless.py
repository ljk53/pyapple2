#!/usr/bin/env python3
"""
Headless Apple II emulator - runs without GUI, outputs to console.
"""

from __future__ import annotations

import sys
import time
import argparse

from headless import headless_boot, boot_to_prompt


def main() -> int:
    parser = argparse.ArgumentParser(description="Headless Apple II emulator")
    parser.add_argument("-R", "--rom", default=None, help="ROM file to use")
    parser.add_argument("-n", "--steps", type=int, default=5000000, help="Max steps (instructions) to run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show progress")
    parser.add_argument("-c", "--command", help="BASIC command to run after boot")
    parser.add_argument("-d", "--disk", help="Disk image (.dsk/.po) to insert in drive 1")
    parser.add_argument("--disk2", help="Disk image (.dsk/.po) to insert in drive 2")
    args = parser.parse_args()

    print(f"Running up to {args.steps} steps...")
    start_time = time.time()

    runtime, display, keyboard = headless_boot(
        rom=args.rom, disk=args.disk, disk2=args.disk2,
        max_steps=args.steps,
    )

    elapsed = time.time() - start_time
    steps_run = args.steps  # approximate; boot_to_prompt may exit early
    print(f"\nBooted in {elapsed:.2f}s")

    if display.has_prompt():
        print("*** PROMPT ']' FOUND! Apple II booted successfully! ***")

    # If a command was provided, type it
    if args.command and display.has_prompt():
        print(f"\nTyping command: {args.command}")
        keyboard.type_string(args.command)

        # Run more cycles to process the command
        boot_to_prompt(runtime.cpu, display, 1000000)

    print("\n=== Screen Content ===")
    print("-" * 42)
    print("|" + display.get_screen().replace("\n", "|\n|") + "|")
    print("-" * 42)

    return 0 if display.has_prompt() else 1


if __name__ == "__main__":
    sys.exit(main())
