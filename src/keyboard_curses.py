from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import curses
    from runtime import Runtime

import curses
from keyboard import KeyboardBase


class Keyboard(KeyboardBase):

    def __init__(self, win: curses.window, runtime: Runtime) -> None:
        KeyboardBase.__init__(self, runtime)
        self.win = win
        curses.noecho()
        win.nodelay(True)

    def run(self) -> None:
        try:
            key = self.win.getkey()
            self.pressed(key)
        except curses.error:
            pass
        except TypeError:
            pass
