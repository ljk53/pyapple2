# Original Source: https://github.com/jtauber/applepy

from __future__ import annotations

import wave
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime import Runtime


class Cassette:

    def __init__(self, fn: str, runtime: Runtime) -> None:
        wav = wave.open(fn, "r")
        self.raw: bytes = wav.readframes(wav.getnframes())
        self.start_cycle: int = 0
        self.start_offset: int = 0

        for i, b in enumerate(self.raw):
            if b > 0xA0:
                self.start_offset = i
                break

        self.runtime: Runtime = runtime
        runtime.subscribe_to_read([0xC060], self.read_byte)

    def read_byte(self, addr: int) -> int:
        cycle = self.runtime.cycle()
        if self.start_cycle == 0:
            self.start_cycle = cycle
        offset = self.start_offset + (cycle - self.start_cycle) * 22000 // 1000000
        return self.raw[offset] if offset < len(self.raw) else 0x80
