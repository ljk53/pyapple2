# Original Source: https://github.com/jtauber/applepy

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime import Runtime

import pygame


class Display:

    characters = [
        [0b00000, 0b01110, 0b10001, 0b10101, 0b10111, 0b10110, 0b10000, 0b01111],
        [0b00000, 0b00100, 0b01010, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001],
        [0b00000, 0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
        [0b00000, 0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
        [0b00000, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
        [0b00000, 0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
        [0b00000, 0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
        [0b00000, 0b01111, 0b10000, 0b10000, 0b10000, 0b10011, 0b10001, 0b01111],
        [0b00000, 0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
        [0b00000, 0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
        [0b00000, 0b00001, 0b00001, 0b00001, 0b00001, 0b00001, 0b10001, 0b01110],
        [0b00000, 0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
        [0b00000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
        [0b00000, 0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
        [0b00000, 0b10001, 0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001],
        [0b00000, 0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
        [0b00000, 0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
        [0b00000, 0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101],
        [0b00000, 0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
        [0b00000, 0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110],
        [0b00000, 0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
        [0b00000, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
        [0b00000, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
        [0b00000, 0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
        [0b00000, 0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
        [0b00000, 0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
        [0b00000, 0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
        [0b00000, 0b11111, 0b11000, 0b11000, 0b11000, 0b11000, 0b11000, 0b11111],
        [0b00000, 0b00000, 0b10000, 0b01000, 0b00100, 0b00010, 0b00001, 0b00000],
        [0b00000, 0b11111, 0b00011, 0b00011, 0b00011, 0b00011, 0b00011, 0b11111],
        [0b00000, 0b00000, 0b00000, 0b00100, 0b01010, 0b10001, 0b00000, 0b00000],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b11111],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
        [0b00000, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100],
        [0b00000, 0b01010, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
        [0b00000, 0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010],
        [0b00000, 0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100],
        [0b00000, 0b11000, 0b11001, 0b00010, 0b00100, 0b01000, 0b10011, 0b00011],
        [0b00000, 0b01000, 0b10100, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101],
        [0b00000, 0b00100, 0b00100, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
        [0b00000, 0b00100, 0b01000, 0b10000, 0b10000, 0b10000, 0b01000, 0b00100],
        [0b00000, 0b00100, 0b00010, 0b00001, 0b00001, 0b00001, 0b00010, 0b00100],
        [0b00000, 0b00100, 0b10101, 0b01110, 0b00100, 0b01110, 0b10101, 0b00100],
        [0b00000, 0b00000, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0b00000],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100, 0b00100, 0b01000],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
        [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100],
        [0b00000, 0b00000, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b00000],
        [0b00000, 0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
        [0b00000, 0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
        [0b00000, 0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111],
        [0b00000, 0b11111, 0b00001, 0b00010, 0b00110, 0b00001, 0b10001, 0b01110],
        [0b00000, 0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
        [0b00000, 0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
        [0b00000, 0b00111, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
        [0b00000, 0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
        [0b00000, 0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
        [0b00000, 0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b11100],
        [0b00000, 0b00000, 0b00000, 0b00100, 0b00000, 0b00100, 0b00000, 0b00000],
        [0b00000, 0b00000, 0b00000, 0b00100, 0b00000, 0b00100, 0b00100, 0b01000],
        [0b00000, 0b00010, 0b00100, 0b01000, 0b10000, 0b01000, 0b00100, 0b00010],
        [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b11111, 0b00000, 0b00000],
        [0b00000, 0b01000, 0b00100, 0b00010, 0b00001, 0b00010, 0b00100, 0b01000],
        [0b00000, 0b01110, 0b10001, 0b00010, 0b00100, 0b00100, 0b00000, 0b00100],
    ]

    lores_colours = [
        (0, 0, 0),  # black
        (208, 0, 48),  # magenta / dark red
        (0, 0, 128),  # dark blue
        (255, 0, 255),  # purple / violet
        (0, 128, 0),  # dark green
        (128, 128, 128),  # gray 1
        (0, 0, 255),  # medium blue / blue
        (96, 160, 255),  # light blue
        (128, 80, 0),  # brown / dark orange
        (255, 128, 0),  # orange
        (192, 192, 192),  # gray 2
        (255, 144, 128),  # pink / light red
        (0, 255, 0),  # light green / green
        (255, 255, 0),  # yellow / light orange
        (64, 255, 144),  # aquamarine / light green
        (255, 255, 255),  # white
    ]

    def __init__(self, runtime: Runtime) -> None:
        self.screen: pygame.Surface = pygame.display.set_mode((560, 384))
        pygame.display.set_caption("ApplePy")
        self.mix: bool = False
        self.flash_time: float = time.time()
        self.flash_on: bool = False
        self.flash_chars: list[list[int]] = [[0] * 0x400] * 2

        self.page: int = 1
        self.text: bool = True
        self.high_res: bool = False
        self.colour: bool = False

        self.chargen: list[list[list[pygame.Surface]]] = []
        for c in self.characters:
            chars = [
                [pygame.Surface((14, 16)), pygame.Surface((14, 16))],
                [pygame.Surface((14, 16)), pygame.Surface((14, 16))],
            ]
            for colour in (0, 1):
                hue = (255, 255, 255) if colour else (0, 200, 0)
                for inv in (0, 1):
                    pixels = pygame.PixelArray(chars[colour][inv])
                    off = hue if inv else (0, 0, 0)
                    on = (0, 0, 0) if inv else hue
                    for row in range(8):
                        b = c[row] << 1
                        for col in range(7):
                            bit = (b >> (6 - col)) & 1
                            pixels[2 * col][2 * row] = on if bit else off  # type: ignore[index]
                            pixels[2 * col + 1][2 * row] = on if bit else off  # type: ignore[index]
                    del pixels
            self.chargen.append(chars)

        self.mount(runtime)

    def txtclr(self, addr: int) -> None:
        self.text = False

    def txtset(self, addr: int) -> None:
        self.text = True
        self.colour = False

    def mixclr(self, addr: int) -> None:
        self.mix = False

    def mixset(self, addr: int) -> None:
        self.mix = True
        self.colour = True

    def lowscr(self, addr: int) -> None:
        self.page = 1

    def hiscr(self, addr: int) -> None:
        self.page = 2

    def lores(self, addr: int) -> None:
        self.high_res = False

    def hires(self, addr: int) -> None:
        self.high_res = True

    def update(self, address: int, value: int) -> None:
        if self.page == 1:
            start_text = 0x400
            start_hires = 0x2000
        elif self.page == 2:
            start_text = 0x800
            start_hires = 0x4000
        else:
            return

        if start_text <= address <= start_text + 0x3FF:
            base = address - start_text
            self.flash_chars[self.page - 1][base] = value
            hi, lo = divmod(base, 0x80)
            row_group, column = divmod(lo, 0x28)
            row = hi + 8 * row_group

            if row_group == 3:
                return

            if self.text or not self.mix or not row < 20:
                mode, ch = divmod(value, 0x40)

                if mode == 0:
                    inv = True
                elif mode == 1:
                    inv = self.flash_on
                else:
                    inv = False

                self.screen.blit(self.chargen[ch][self.colour][inv], (2 * (column * 7), 2 * (row * 8)))
            else:
                pixels = pygame.PixelArray(self.screen)
                if not self.high_res:
                    lower, upper = divmod(value, 0x10)

                    for dx in range(14):
                        for dy in range(8):
                            x = column * 14 + dx
                            y = row * 16 + dy
                            pixels[x][y] = self.lores_colours[upper]  # type: ignore[index]
                        for dy in range(8, 16):
                            x = column * 14 + dx
                            y = row * 16 + dy
                            pixels[x][y] = self.lores_colours[lower]  # type: ignore[index]
                del pixels

        elif start_hires <= address <= start_hires + 0x1FFF:
            if self.high_res:
                base = address - start_hires
                row8, b = divmod(base, 0x400)
                hi, lo = divmod(b, 0x80)
                row_group, column = divmod(lo, 0x28)
                row = 8 * (hi + 8 * row_group) + row8

                if self.mix and row >= 160:
                    return

                if row < 192 and column < 40:

                    pixels = pygame.PixelArray(self.screen)
                    msb = value // 0x80

                    for b in range(7):
                        c = value & (1 << b)
                        xx = column * 7 + b
                        x = 2 * xx
                        y = 2 * row

                        if msb:
                            if xx % 2:
                                pixels[x][y] = (0, 0, 0)  # type: ignore[index]
                                # orange
                                pixels[x][y] = (255, 192, 0) if c else (0, 0, 0)  # type: ignore[index]  # @@@
                                pixels[x + 1][y] = (255, 192, 0) if c else (0, 0, 0)  # type: ignore[index]
                            else:
                                # blue
                                pixels[x][y] = (0, 192, 255) if c else (0, 0, 0)  # type: ignore[index]
                                pixels[x + 1][y] = (0, 0, 0)  # type: ignore[index]
                                pixels[x + 1][y] = (0, 192, 255) if c else (0, 0, 0)  # type: ignore[index]  # @@@
                        else:
                            if xx % 2:
                                pixels[x][y] = (0, 0, 0)  # type: ignore[index]
                                # green
                                pixels[x][y] = (0, 255, 0) if c else (0, 0, 0)  # type: ignore[index]  # @@@
                                pixels[x + 1][y] = (0, 255, 0) if c else (0, 0, 0)  # type: ignore[index]
                            else:
                                # violet
                                pixels[x][y] = (255, 0, 255) if c else (0, 0, 0)  # type: ignore[index]
                                pixels[x + 1][y] = (0, 0, 0)  # type: ignore[index]
                                pixels[x + 1][y] = (255, 0, 255) if c else (0, 0, 0)  # type: ignore[index]  # @@@

                        pixels[x][y + 1] = (0, 0, 0)  # type: ignore[index]
                        pixels[x + 1][y + 1] = (0, 0, 0)  # type: ignore[index]

                    del pixels

    def flash(self) -> None:
        if time.time() - self.flash_time >= 0.5:
            self.flash_on = not self.flash_on
            for offset, char in enumerate(self.flash_chars[self.page - 1]):
                if (char & 0xC0) == 0x40:
                    self.update(0x400 + offset, char)
            self.flash_time = time.time()

    def mount(self, runtime: Runtime) -> None:
        for addr, method in [
            (0xC050, self.txtclr),
            (0xC051, self.txtset),
            (0xC052, self.mixclr),
            (0xC053, self.mixset),
            (0xC054, self.lowscr),
            (0xC055, self.hiscr),
            (0xC056, self.lores),
            (0xC057, self.hires),
        ]:
            runtime.subscribe_to_read([addr], method)
            runtime.subscribe_to_write([addr], lambda a, v, m=method: m(a))
        runtime.subscribe_to_write(range(0x400, 0xC00), self.update)
        runtime.subscribe_to_write(range(0x2000, 0x6000), self.update)
