from __future__ import annotations

import argparse

import options
import curses
from runtime import Runtime
from display_curses import Display
from keyboard_curses import Keyboard


class Looper:

    def __init__(self) -> None:
        self.options: argparse.Namespace = options.get_options()
        self.runtime: Runtime = Runtime(self.options)

        # Steps (instructions) per iteration.  Smaller than pygame because
        # there is no frame-rate cap; the loop runs as fast as possible.
        # With -T/--throttle, cpu_throttle.py sleeps inside run() to keep
        # effective cycle rate at 1.023 MHz.
        self._steps_per_frame: int = 4096 if self.options.disk else 256

    def start(self) -> None:
        curses.wrapper(self.run)

    def run(self, win: curses.window) -> None:
        self.display: Display = Display(win, self.runtime)
        self.keyboard: Keyboard = Keyboard(win, self.runtime)

        while True:
            self.keyboard.run()
            self.runtime.run(self._steps_per_frame)


if __name__ == "__main__":
    looper = Looper()
    looper.start()
