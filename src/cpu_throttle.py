"""CPU throttle: sync emulated cycle count to wall-clock at 1.023 MHz.

The 6502 idle-loop short-circuits in MPU (keyboard polling, tight DEY/BNE)
inflate processorCycles by thousands per step.  A naive "run N steps then
sleep" approach overshoots by orders of magnitude.

Solution: cycle-budgeted stepping.  Each run() call gets a cycle budget
equal to the wall-clock time available (frame_seconds * 1.023 MHz).
We step the CPU until the budget is consumed, then sleep the remainder.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Protocol

    class _Steppable(Protocol):
        def step(self) -> object: ...

APPLE_II_CLOCK_HZ = 1_023_000  # 1.023 MHz


class CpuThrottle:
    """Cycle-budgeted throttle that keeps emulation at 1.023 MHz."""

    def __init__(self, initial_cycles: int = 0) -> None:
        self._wall0: float = time.perf_counter()
        self._cyc0: int = initial_cycles
        # Cap per-sleep so the caller's event loop stays responsive.
        # At 30 fps a frame is 33 ms; 30 ms keeps us under one frame.
        self._max_sleep: float = 0.030  # 30 ms
        self._drift_reset: float = 0.5  # reset baseline if >500 ms behind

    def run_throttled(self, cpu: _Steppable, get_cycles: callable, steps: int) -> None:  # type: ignore[valid-type]
        """Step *cpu* up to *steps* times, sleeping to match 1.023 MHz.

        After each small batch of steps we compare emulated cycles to wall
        time.  If the emulator is ahead we sleep (capped at ``_max_sleep``
        to keep the event loop responsive) and return.

        The sleep cap matters because MPU idle-loop short-circuits can add
        thousands of synthetic cycles per step (keyboard poll: 4352
        cycles/step).  Without the cap, 128 poll steps would block for
        ~544 ms, starving the event loop.

        For normal code the check interval is large enough (1024 steps ≈
        4K cycles ≈ 4 ms) that the overhead of ``perf_counter()`` calls
        is negligible (<0.1% of wall time).
        """
        check = min(steps, 1024)
        done = 0
        while done < steps:
            batch = min(check, steps - done)
            for _ in range(batch):
                cpu.step()
            done += batch

            # Compare emulated time to wall time
            current_cycles = get_cycles()
            elapsed_cyc = current_cycles - self._cyc0
            expected = elapsed_cyc / APPLE_II_CLOCK_HZ
            actual = time.perf_counter() - self._wall0
            ahead = expected - actual

            if ahead > self._max_sleep:
                # Far ahead (idle-loop inflation) — cap sleep, return.
                time.sleep(self._max_sleep)
                return
            elif ahead > 0.002:
                # Moderately ahead — sleep the exact amount, return.
                time.sleep(ahead)
                return
            elif ahead < -self._drift_reset:
                # Fell far behind (OS stall, window drag) — reset baseline.
                self._wall0 = time.perf_counter()
                self._cyc0 = current_cycles

    def reset(self) -> None:
        self._wall0 = time.perf_counter()
        self._cyc0 = 0
