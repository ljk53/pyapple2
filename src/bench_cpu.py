#!/usr/bin/env python3
"""Micro-benchmarks for CPU + memory performance.

Terminology (see L1_emulator_timing.md):
    step  — one cpu.step() call = one 6502 instruction
    cycle — 6502 clock cycles (2–7 per step, tracked by MPU.processorCycles)
    wall  — real elapsed seconds (time.perf_counter)

Usage:
    python3 bench_cpu.py
"""

from __future__ import annotations

import argparse
import os
import time

import memory
from headless import HeadlessDisplay, HeadlessKeyboard
from runtime import Runtime


def make_env(disk: str | None = None):
    """Build a headless emulator environment using Runtime."""
    opts = argparse.Namespace(
        rom=None, ram=None,
        disk=disk, disk2=None,
        throttle=False, controller=None,
    )
    runtime = Runtime(opts)
    display = HeadlessDisplay(runtime.bus)
    keyboard = HeadlessKeyboard(runtime.bus)
    return runtime, display, keyboard


def bench_step(label: str, n: int, disk: str | None = None) -> float:
    """Benchmark N CPU steps and return steps/sec."""
    runtime, display, keyboard = make_env(disk)
    cpu = runtime.cpu
    # Warmup
    for _ in range(10000):
        cpu.step()
    cyc0 = cpu.processorCycles
    start = time.perf_counter()
    for _ in range(n):
        cpu.step()
    elapsed = time.perf_counter() - start
    cycles = cpu.processorCycles - cyc0
    step_rate = n / elapsed
    eff_mhz = cycles / elapsed / 1_000_000
    print(f"  {label}: {n:,} steps in {elapsed:.3f}s")
    print(f"    {step_rate:,.0f} steps/sec, {cycles:,} cycles ({cycles/n:.1f} cyc/step)")
    print(f"    effective {eff_mhz:.2f} MHz ({eff_mhz/1.023:.1f}x Apple II)")
    return step_rate


def bench_memory_read(label: str, n: int) -> float:
    """Benchmark N raw memory reads."""
    mem_obj = memory.ObservableMemory()
    # Subscribe to a few addresses (simulating keyboard/display)
    mem_obj.subscribe_to_read([0xC000], lambda a: 0)
    mem_obj.subscribe_to_write(range(0x400, 0x800), lambda a, v: None)

    start = time.perf_counter()
    for i in range(n):
        mem_obj[i & 0xFFFF]
    elapsed = time.perf_counter() - start
    rate = n / elapsed
    print(f"  {label}: {n:,} reads in {elapsed:.3f}s = {rate:,.0f} reads/sec")
    return rate


def bench_memory_write(label: str, n: int) -> float:
    """Benchmark N raw memory writes."""
    mem_obj = memory.ObservableMemory()
    mem_obj.subscribe_to_write(range(0x400, 0x800), lambda a, v: None)

    start = time.perf_counter()
    for i in range(n):
        mem_obj[i & 0xFFFF] = 0
    elapsed = time.perf_counter() - start
    rate = n / elapsed
    print(f"  {label}: {n:,} writes in {elapsed:.3f}s = {rate:,.0f} writes/sec")
    return rate


def bench_dos_boot(label: str) -> float:
    """Benchmark DOS 3.3 boot to full prompt."""
    disk_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "APPLER.DSK")
    runtime, display, keyboard = make_env(disk_path)
    cpu = runtime.cpu
    cyc0 = cpu.processorCycles
    start = time.perf_counter()
    steps = 0
    for batch in range(200):
        for _ in range(250_000):
            cpu.step()
        steps = (batch + 1) * 250_000
        screen = display.get_screen()
        in_keyin = 0xFD1B <= cpu.pc <= 0xFD24
        if "DOS VERSION" in screen and in_keyin:
            break

    elapsed = time.perf_counter() - start
    cycles = cpu.processorCycles - cyc0
    step_rate = steps / elapsed
    eff_mhz = cycles / elapsed / 1_000_000
    print(f"  {label}: {steps:,} steps in {elapsed:.3f}s")
    print(f"    {step_rate:,.0f} steps/sec, {cycles:,} cycles ({cycles/steps:.1f} cyc/step)")
    print(f"    effective {eff_mhz:.2f} MHz ({eff_mhz/1.023:.1f}x Apple II)")
    return elapsed


if __name__ == "__main__":
    print("=== Memory Read ===")
    bench_memory_read("ObservableMemory read", 2_000_000)

    print("\n=== Memory Write ===")
    bench_memory_write("ObservableMemory write", 2_000_000)

    print("\n=== CPU Step (ROM boot, includes idle-loop short-circuits) ===")
    bench_step("MPU.step", 2_000_000)

    print("\n=== DOS 3.3 Boot (full, to banner+prompt) ===")
    bench_dos_boot("DOS 3.3 boot")

    print()
    print("Note: cyc/step >> 7 indicates idle-loop short-circuits are active.")
    print("      See L1_emulator_timing.md for step vs cycle terminology.")
