from __future__ import annotations

import curses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime import Runtime


class Display:

    def __init__(self, win: curses.window, runtime: Runtime) -> None:
        self.win = win
        runtime.subscribe_to_write(range(0x400, 0x800), self.write)
        win.clear()

    def write(self, address: int, value: int) -> None:
        base = address - 0x400
        hi, lo = divmod(base, 0x80)
        row_group, column = divmod(lo, 0x28)
        row = hi + 8 * row_group

        # skip if writing to row group 3
        if row_group == 3:
            return

        c = chr(0x20 + ((value + 0x20) % 0x40))

        if value < 0x40:
            attr = curses.A_DIM
        elif value < 0x80:
            attr = curses.A_REVERSE
        elif value < 0xA0:
            attr = curses.A_UNDERLINE
        else:
            attr = curses.A_DIM

        try:
            self.win.addch(row, column, c, attr)
        except curses.error:
            pass
