# Original Source: https://github.com/jtauber/applepy

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime import Runtime

import pygame
import numpy


class Speaker:

    CPU_CYCLES_PER_SAMPLE: int = 60
    CHECK_INTERVAL: int = 1000
    last_toggle: int | None
    buffer: list[int]
    polarity: bool

    def __init__(self, runtime: Runtime) -> None:
        try:
            pygame.mixer.pre_init(11025, -16, 1)
        except NotImplementedError:
            pass
        pygame.init()
        self.reset()
        self.runtime: Runtime = runtime
        runtime.subscribe_to_read([0xC030], self.toggle)

    def toggle(self, addr: int) -> None:
        cycle = self.runtime.cycle()
        if self.last_toggle is not None:
            l = (cycle - self.last_toggle) // Speaker.CPU_CYCLES_PER_SAMPLE
            self.buffer.extend([0, 26000] if self.polarity else [0, -2600])
            self.buffer.extend((l - 2) * [16384] if self.polarity else [-16384])
            self.polarity = not self.polarity
        self.last_toggle = cycle

    def reset(self) -> None:
        self.last_toggle = None
        self.buffer = []
        self.polarity = False

    def play(self) -> None:
        try:
            sample_array = numpy.int16(self.buffer)  # type: ignore[arg-type]
            sound = pygame.sndarray.make_sound(sample_array)  # type: ignore[arg-type]
            sound.play()
        except NotImplementedError:
            pass
        self.reset()

    def update(self, cycle: int) -> None:
        if self.buffer and self.last_toggle is not None and (cycle - self.last_toggle) > self.CHECK_INTERVAL:
            self.play()
