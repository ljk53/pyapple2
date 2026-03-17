from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import cpu_mpu6502
import memory
import control_handler
from cpu_throttle import CpuThrottle
from disk2 import Disk2Controller

if TYPE_CHECKING:
    import argparse


class Memory:

    def __init__(self, options: argparse.Namespace | None = None) -> None:
        self._mem = memory.ObservableMemory()

        if options and options.rom:
            self.load_file(0xD000, options.rom)

        if options and options.ram:
            self.load_file(0x0000, options.ram)

    def load(self, address: int, data: bytes | list[int]) -> None:
        for offset, datum in enumerate(data):
            self._mem[address + offset] = datum

    def load_file(self, address: int, filename: str) -> None:
        with open(filename, "rb") as f:
            for offset, datum in enumerate(f.read()):
                self._mem[address + offset] = datum

    def read_byte(self, address: int) -> int:
        return self._mem[address]

    def write_byte(self, address: int, value: int) -> None:
        if address < 0xC000:
            self._mem[address] = value
        elif address < 0xC100:
            # I/O space ($C000-$C0FF): let writes trigger callbacks
            self._mem[address] = value

    def __getitem__(self, key: int) -> int:
        return self._mem[key]

    def __setitem__(self, key: int, value: int) -> None:
        if key < 0xC100:
            self._mem[key] = value


class Runtime:

    def __init__(self, options: argparse.Namespace | None = None) -> None:
        self.memory: Memory = Memory(options)
        self.create_cpu()
        self.control_server: control_handler.ControlServer | None = None
        if options and options.controller:
            self.control_server = control_handler.create_controller(self, options.controller)
        self._throttle: CpuThrottle | None = None
        if options and getattr(options, "throttle", False):
            self._throttle = CpuThrottle()
        self._exec_counts: bytearray | None = None

        # Mount disk controller if specified
        self.disk2: Disk2Controller | None = None
        if options and getattr(options, "disk", None):
            self.disk2 = Disk2Controller.attach(
                self.memory._mem, options.disk, getattr(options, "disk2", None)
            )

        self.reset()

    def run(self, steps: int = 256) -> None:
        if self.control_server:
            self.control_server.handle(0)
        if self._throttle is not None:
            self._throttle.run_throttled(self.cpu, self.cycle, steps)
        elif self._exec_counts is not None:
            ec = self._exec_counts
            cpu = self.cpu
            for i in range(steps):
                cpu.step()
                if i & 127 == 0:
                    pc = cpu.pc
                    c = ec[pc]
                    if c < 255:
                        ec[pc] = c + 1
        else:
            for _ in range(steps):
                self.cpu.step()

    def reset(self) -> None:
        self.cpu.reset()
        self.set_pc(self.read_word(0xFFFC))
        if self._throttle is not None:
            self._throttle.reset()

    def create_cpu(self) -> None:
        self.cpu: cpu_mpu6502.MPU = cpu_mpu6502.MPU(self.memory)  # type: ignore[arg-type]

    def set_pc(self, pc: int) -> None:
        self.cpu.pc = pc

    def cycle(self) -> int:
        return self.cpu.processorCycles

    def get_status(self) -> dict[str, int]:
        return dict(
            (x, getattr(self, x))
            for x in (
                "accumulator",
                "x_index",
                "y_index",
                "stack_pointer",
                "program_counter",
                "sign_flag",
                "overflow_flag",
                "break_flag",
                "decimal_mode_flag",
                "interrupt_disable_flag",
                "zero_flag",
                "carry_flag",
            )
        )

    def __getattr__(self, name: str) -> Any:
        if name == "accumulator":
            return self.cpu.a
        elif name == "x_index":
            return self.cpu.x
        elif name == "y_index":
            return self.cpu.y
        elif name == "stack_pointer":
            return self.cpu.sp
        elif name == "program_counter":
            return self.cpu.pc
        elif name == "sign_flag":
            return self.cpu.p & self.cpu.NEGATIVE
        elif name == "overflow_flag":
            return self.cpu.p & self.cpu.OVERFLOW
        elif name == "break_flag":
            return self.cpu.p & self.cpu.BREAK
        elif name == "decimal_mode_flag":
            return self.cpu.p & self.cpu.DECIMAL
        elif name == "interrupt_disable_flag":
            return self.cpu.p & self.cpu.INTERRUPT
        elif name == "zero_flag":
            return self.cpu.p & self.cpu.ZERO
        elif name == "carry_flag":
            return self.cpu.p & self.cpu.CARRY
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def read_byte(self, address: int) -> int:
        return self.memory[address]

    def read_word(self, address: int) -> int:
        return self.memory[address] + (self.memory[address + 1] << 8)

    def write_byte(self, address: int, value: int) -> None:
        self.memory[address] = value

    @property
    def bus(self) -> memory.ObservableMemory:
        """The underlying ObservableMemory bus for peripheral mounting."""
        return self.memory._mem

    def subscribe_to_read(self, address_range: range | list[int], callback: Callable[..., int | None]) -> None:
        self.memory._mem.subscribe_to_read(address_range, callback)

    def subscribe_to_write(self, address_range: range | list[int], callback: Callable[..., int | None]) -> None:
        self.memory._mem.subscribe_to_write(address_range, callback)

    def enable_write_tracking(self) -> None:
        self.memory._mem.enable_write_tracking()

    def get_write_counts(self) -> bytearray | None:
        return self.memory._mem.get_write_counts()

    def clear_write_counts(self) -> None:
        self.memory._mem.clear_write_counts()

    def enable_activity_tracking(self) -> None:
        """Enable read, write, and execute tracking for heatmap."""
        self.memory._mem.enable_read_tracking()
        self.memory._mem.enable_write_tracking()
        self._exec_counts = bytearray(65536)

    def get_activity(self) -> tuple[bytearray, bytearray, bytearray] | None:
        """Return (read_counts, write_counts, exec_counts) or None."""
        rc = self.memory._mem.get_read_counts()
        wc = self.memory._mem.get_write_counts()
        ec = self._exec_counts
        if rc is None or wc is None or ec is None:
            return None
        return (rc, wc, ec)

    def toggle_throttle(self) -> bool:
        """Toggle CPU throttle. Returns True if now throttled."""
        if self._throttle is not None:
            self._throttle = None
            return False
        else:
            self._throttle = CpuThrottle(self.cycle())
            return True

    @property
    def throttled(self) -> bool:
        return self._throttle is not None

    def clear_activity(self) -> None:
        """Reset all activity counters to zero."""
        self.memory._mem.clear_read_counts()
        self.memory._mem.clear_write_counts()
        if self._exec_counts is not None:
            for i in range(len(self._exec_counts)):
                self._exec_counts[i] = 0
