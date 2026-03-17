"""
Shared headless Apple II components.

All classes mount to an ObservableMemory bus via subscribe_to_read/write.

Components:
  HeadlessDisplay  — text-mode screen capture (page 1)
  HeadlessKeyboard — programmable keyboard input queue
  SoftSwitchTracker — tracks display mode soft-switches ($C050-$C057)
  NullInput        — stubs all input hardware to 'not pressed'

Factory:
  headless_boot()  — create Runtime + headless peripherals, boot to prompt
"""

from __future__ import annotations

import argparse
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Protocol

    class _HasStep(Protocol):
        def step(self) -> None: ...

    class _HasPrompt(Protocol):
        def has_prompt(self) -> bool: ...

    from memory import ObservableMemory
    from runtime import Runtime


class HeadlessDisplay:
    """Text-mode display that captures screen memory writes."""

    def __init__(self, mem: ObservableMemory) -> None:
        """Initialize with an ObservableMemory instance."""
        self.screen: list[list[str]] = [[" " for _ in range(40)] for _ in range(24)]
        mem.subscribe_to_write(range(0x400, 0x800), self._on_write)

    def _on_write(self, address: int, value: int) -> None:
        base = address - 0x400
        hi, lo = divmod(base, 0x80)
        row_group, column = divmod(lo, 0x28)
        row = hi + 8 * row_group

        if row_group == 3 or row >= 24 or column >= 40:
            return

        self.screen[row][column] = chr(0x20 + ((value + 0x20) % 0x40))

    def get_screen(self) -> str:
        return "\n".join("".join(row) for row in self.screen)

    def has_prompt(self) -> bool:
        """Check if the ']' BASIC prompt is visible on screen."""
        for row in self.screen:
            if "".join(row).strip().startswith("]"):
                return True
        return False

    def count_prompts(self) -> int:
        """Count lines that start with ']' prompt."""
        count = 0
        for row in self.screen:
            if "".join(row).strip().startswith("]"):
                count += 1
        return count


class HeadlessKeyboard:
    """Keyboard that can be programmed with input."""

    def __init__(self, mem: ObservableMemory) -> None:
        """Initialize with an ObservableMemory instance."""
        self.buf: list[int] = []
        self.kbd: int = 0
        mem.subscribe_to_read([0xC000], lambda addr: self.kbd)
        # Any access to $C010 clears the keyboard strobe.
        mem.subscribe_to_read([0xC010], self._clear)
        mem.subscribe_to_write([0xC010], lambda addr, val: self.pop())

    def push(self, kbd: int) -> None:
        if self.kbd & 0x80:
            self.buf.append(kbd)
        else:
            self.kbd = kbd

    def pop(self) -> None:
        if self.buf:
            self.kbd = self.buf.pop(0)
        else:
            self.kbd &= 0x7F

    def _clear(self, addr: int) -> int:
        self.pop()
        return 0

    def type_key(self, key: str | int) -> None:
        """Simulate typing a single key."""
        if isinstance(key, str):
            key = ord(key)
        self.push(0x80 | key)

    def type_string(self, s: str) -> None:
        """Type a string followed by CR."""
        for ch in s:
            self.push(0x80 | ord(ch))
        self.push(0x80 | 0x0D)


class SoftSwitchTracker:
    """Track Apple II display soft-switch state via the memory bus.

    Mounts to $C050-$C057 (both reads and writes) and maintains
    the current display mode: text/graphics, hires/lores, page 1/2, mixed.
    """

    def __init__(self, mem: ObservableMemory) -> None:
        self.page: int = 1
        self.hires: bool = False
        self.text: bool = True
        self.mix: bool = False

        for addr, attr, val in [
            (0xC050, "text", False),
            (0xC051, "text", True),
            (0xC052, "mix", False),
            (0xC053, "mix", True),
            (0xC054, "page", 1),
            (0xC055, "page", 2),
            (0xC056, "hires", False),
            (0xC057, "hires", True),
        ]:
            a, v = attr, val
            mem.subscribe_to_write([addr], lambda _a, _v, a=a, v=v: setattr(self, a, v))  # type: ignore[misc]
            mem.subscribe_to_read(
                [addr],
                lambda _a, a=a, v=v: (setattr(self, a, v), None)[-1],  # type: ignore[misc,func-returns-value]
            )

    def get_state(self) -> dict[str, int | bool]:
        return {"page": self.page, "hires": self.hires, "text": self.text, "mix": self.mix}


class NullInput:
    """Stub all Apple II input to 'not pressed'.

    Mounts keyboard ($C000/$C010), buttons ($C061/$C062),
    and paddles ($C064/$C070) to always return 0.
    """

    def __init__(self, mem: ObservableMemory) -> None:
        for addr in [0xC000, 0xC010, 0xC061, 0xC062, 0xC064, 0xC070]:
            mem.subscribe_to_read([addr], lambda _a: 0x00)


def boot_to_prompt(cpu: _HasStep, display: _HasPrompt, max_steps: int = 5000000) -> int:
    """Run CPU until ']' prompt appears or *max_steps* instructions executed.

    Returns number of steps (instructions) executed.
    """
    steps = 0
    while steps < max_steps:
        cpu.step()
        steps += 1
        if steps % 10000 == 0 and display.has_prompt():
            break
    return steps


def headless_boot(
    rom: str | None = None,
    disk: str | None = None,
    disk2: str | None = None,
    max_steps: int = 5_000_000,
) -> tuple[Runtime, HeadlessDisplay, HeadlessKeyboard]:
    """Create a headless Apple II environment booted to the BASIC prompt.

    Builds a Runtime (CPU + memory + optional disk), mounts a headless
    text display and keyboard, then runs until the ']' prompt appears.

    Args:
        rom: ROM file path (default: bin/A2SOFT2.BIN).
        disk: Disk image for drive 1 (.dsk/.po).
        disk2: Disk image for drive 2.
        max_steps: Maximum instructions to execute during boot.

    Returns:
        (runtime, display, keyboard) tuple ready for interaction.
    """
    from runtime import Runtime  # deferred to avoid circular import

    if rom is None:
        rom = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "A2SOFT2.BIN")

    opts = argparse.Namespace(
        rom=rom, ram=None,
        disk=disk, disk2=disk2,
        throttle=False, controller=None,
    )
    runtime = Runtime(opts)
    display = HeadlessDisplay(runtime.bus)
    keyboard = HeadlessKeyboard(runtime.bus)
    boot_to_prompt(runtime.cpu, display, max_steps)
    return runtime, display, keyboard
