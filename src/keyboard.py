from __future__ import annotations

import options
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime import Runtime


class KeyboardBase:

    def __init__(self, runtime: Runtime) -> None:
        self.buf: list[int] = []
        self.kbd: int = 0
        self.mount(runtime)
        self.load_keylog(options.get_options().keylog)

    def load_keylog(self, filename: str | None) -> None:
        if not filename:
            return
        with open(filename, "r") as f:
            for c in f.read():
                self.pressed(c)

    def push(self, kbd: int) -> None:
        if self.kbd & 0x80:
            self.buf.append(kbd)
        else:
            self.kbd = kbd

    def pop(self) -> None:
        if len(self.buf):
            self.kbd = self.buf[0]
            del self.buf[0]
        else:
            self.kbd &= 0x7F

    def pressed(self, value: str) -> None:
        key = value and ord(value[0]) or 0
        if key == 0xA:
            key = 0xD
        elif key == 0x7F:
            key = 0x8
        self.push(0x80 | key)

    def mount(self, runtime: Runtime) -> None:
        runtime.subscribe_to_read([0xC000], lambda addr: self.kbd)
        # Any access to $C010 clears the keyboard strobe (bit 7 of $C000).
        # Programs use both LDA $C010 (read) and STA $C010 (write).
        runtime.subscribe_to_read([0xC010], self.clear)
        runtime.subscribe_to_write([0xC010], lambda addr, val: self.pop())

    def clear(self, addr: int) -> int:
        self.pop()
        return 0
