from __future__ import annotations

import argparse

import pygame
import options
from runtime import Runtime
from display_pygame import Display
from speaker_pygame import Speaker
from keyboard_pygame import Keyboard
from cassette import Cassette


class Looper:

    def __init__(self) -> None:
        self.options: argparse.Namespace = options.get_options()
        self.runtime: Runtime = Runtime(self.options)
        self.display: Display = Display(self.runtime)
        self.speaker: Speaker | None = None if self.options.quiet else Speaker(self.runtime)
        self.cassette: Cassette | None = (
            Cassette(self.options.cassette, self.runtime) if self.options.cassette else None
        )
        self.keyboard: Keyboard = Keyboard(self.runtime)

        # Steps (instructions) per frame.  At 30 fps with MPU idle-loop
        # short-circuits, 32 K steps ≈ 34 K cycles ≈ 33 ms at 1.023 MHz.
        # Without disk fewer steps are needed (no disk delay loops).
        # With -T/--throttle the cycle-budgeted throttle in cpu_throttle.py
        # may return early from run() to maintain real Apple II speed.
        self._steps_per_frame: int = 32768 if self.options.disk else 8192

    def start(self) -> None:
        clock = pygame.time.Clock()
        quit = False
        while not quit:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    quit = True
                self.keyboard.run(event)

            self.runtime.run(self._steps_per_frame)
            self.display.flash()
            pygame.display.flip()
            if self.speaker:
                self.speaker.update(self.runtime.cycle())
            clock.tick(30)


if __name__ == "__main__":
    looper = Looper()
    looper.start()
