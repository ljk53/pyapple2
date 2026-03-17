"""
Pure-memory bitmap renderer for Apple II display.

Renders text, Lo-Res, and Hi-Res modes to an in-memory RGB pixel buffer
(560x384, 2x scaled) without any GUI dependency. Can export to PNG using
only Python stdlib (struct + zlib).
"""

from __future__ import annotations

import struct
import zlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory import ObservableMemory

# Screen dimensions (2x scaled, same as pygame display)
WIDTH = 560
HEIGHT = 384

# Character bitmaps (same as display_pygame.py)
CHARACTERS = [
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

LORES_COLOURS = [
    (0, 0, 0),  # black
    (208, 0, 48),  # magenta
    (0, 0, 128),  # dark blue
    (255, 0, 255),  # purple
    (0, 128, 0),  # dark green
    (128, 128, 128),  # gray 1
    (0, 0, 255),  # medium blue
    (96, 160, 255),  # light blue
    (128, 80, 0),  # brown
    (255, 128, 0),  # orange
    (192, 192, 192),  # gray 2
    (255, 144, 128),  # pink
    (0, 255, 0),  # green
    (255, 255, 0),  # yellow
    (64, 255, 144),  # aquamarine
    (255, 255, 255),  # white
]


def write_png(pixels: bytearray | bytes, width: int, height: int, path: str) -> None:
    """Write RGB pixel data as PNG using only stdlib."""

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)

    # Build raw image data with filter byte (0 = None) per row
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter: None
        raw.extend(pixels[y * stride : (y + 1) * stride])

    idat = _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    iend = _chunk(b"IEND", b"")

    with open(path, "wb") as f:
        f.write(signature + ihdr + idat + iend)


def render_hires_page(mem: ObservableMemory, page: int = 1) -> tuple[bytearray, int, int]:
    """Render a complete HiRes page from memory to RGB pixels.

    Reads $2000-$3FFF (page 1) or $4000-$5FFF (page 2) and renders
    using the same artifact color logic as BitmapDisplay.

    Returns (pixels, width, height) where pixels is a bytearray of RGB data
    at 560x384 (2x scaled).
    """
    pixels = bytearray(WIDTH * HEIGHT * 3)
    base = 0x2000 if page == 1 else 0x4000

    for y in range(192):
        # Apple II HiRes address interleave
        row_addr = base + (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28

        for col_byte in range(40):
            byte_val = mem[row_addr + col_byte]
            msb = byte_val >> 7

            for bit in range(7):
                pixel_on = (byte_val >> bit) & 1
                xx = col_byte * 7 + bit
                x = 2 * xx
                py = 2 * y

                if pixel_on:
                    if msb:
                        color = (255, 192, 0) if (xx % 2) else (0, 192, 255)
                    else:
                        color = (0, 255, 0) if (xx % 2) else (255, 0, 255)
                else:
                    color = (0, 0, 0)

                # 2x scaled: top row gets color, bottom row stays black
                off = (py * WIDTH + x) * 3
                pixels[off : off + 3] = bytes(color)
                pixels[off + 3 : off + 6] = bytes(color)

    return pixels, WIDTH, HEIGHT


class BitmapDisplay:
    """Pure-memory Apple II display renderer."""

    def __init__(self, mem: ObservableMemory) -> None:
        self.pixels: bytearray = bytearray(WIDTH * HEIGHT * 3)  # RGB
        self.mix: bool = False
        self.flash_on: bool = False
        self.page: int = 1
        self.text: bool = True
        self.colour: bool = False
        self.high_res: bool = False
        self.flash_chars: list[list[int]] = [[0] * 0x400, [0] * 0x400]

        # Pre-render character bitmaps
        self._chargen = self._build_chargen()

        self._mount(mem)

    def _build_chargen(self) -> dict[int, dict[int, dict[int, list[tuple[int, int, tuple[int, int, int]]]]]]:
        """Pre-render all characters as pixel arrays.

        Returns dict: chargen[ch][colour][inv] = list of (x_offset, y_offset, r, g, b)
        """
        chargen: dict[int, dict[int, dict[int, list[tuple[int, int, tuple[int, int, int]]]]]] = {}
        for ch, c in enumerate(CHARACTERS):
            chargen[ch] = {}
            for colour in (0, 1):
                hue = (255, 255, 255) if colour else (0, 200, 0)
                chargen[ch][colour] = {}
                for inv in (0, 1):
                    off = hue if inv else (0, 0, 0)
                    on = (0, 0, 0) if inv else hue
                    char_pixels: list[tuple[int, int, tuple[int, int, int]]] = []
                    for row in range(8):
                        b = c[row] << 1
                        for col in range(7):
                            bit = (b >> (6 - col)) & 1
                            color = on if bit else off
                            # 2x scaled: each pixel becomes 2x2
                            char_pixels.append((2 * col, 2 * row, color))
                            char_pixels.append((2 * col + 1, 2 * row, color))
                    chargen[ch][colour][inv] = char_pixels
        return chargen

    def _set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            offset = (y * WIDTH + x) * 3
            self.pixels[offset] = r
            self.pixels[offset + 1] = g
            self.pixels[offset + 2] = b

    def _blit_char(self, ch: int, colour: int | bool, inv: bool, dest_x: int, dest_y: int) -> None:
        for dx, dy, color in self._chargen[ch][colour][inv]:
            self._set_pixel(dest_x + dx, dest_y + dy, *color)

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

                self._blit_char(ch, self.colour, inv, 2 * (column * 7), 2 * (row * 8))
            else:
                if not self.high_res:
                    lower, upper = divmod(value, 0x10)
                    for dx in range(14):
                        for dy in range(8):
                            x = column * 14 + dx
                            y = row * 16 + dy
                            self._set_pixel(x, y, *LORES_COLOURS[upper])
                        for dy in range(8, 16):
                            x = column * 14 + dx
                            y = row * 16 + dy
                            self._set_pixel(x, y, *LORES_COLOURS[lower])

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
                    msb = value // 0x80

                    for bit in range(7):
                        c = value & (1 << bit)
                        xx = column * 7 + bit
                        x = 2 * xx
                        y = 2 * row

                        if msb:
                            if xx % 2:
                                color = (255, 192, 0) if c else (0, 0, 0)  # orange
                            else:
                                color = (0, 192, 255) if c else (0, 0, 0)  # blue
                        else:
                            if xx % 2:
                                color = (0, 255, 0) if c else (0, 0, 0)  # green
                            else:
                                color = (255, 0, 255) if c else (0, 0, 0)  # violet

                        self._set_pixel(x, y, *color)
                        self._set_pixel(x + 1, y, *color)
                        self._set_pixel(x, y + 1, 0, 0, 0)
                        self._set_pixel(x + 1, y + 1, 0, 0, 0)

    def save_png(self, path: str) -> None:
        """Save the current display to a PNG file."""
        write_png(self.pixels, WIDTH, HEIGHT, path)

    def get_text(self) -> str:
        """Read current text screen content from flash_chars buffer."""
        lines: list[str] = []
        for row in range(24):
            line: list[str] = []
            for col in range(40):
                # Compute address offset for this row/col
                hi = row % 8
                row_group = row // 8
                base = hi * 0x80 + row_group * 0x28 + col
                value = self.flash_chars[self.page - 1][base]
                line.append(chr(0x20 + ((value + 0x20) % 0x40)))
            lines.append("".join(line))
        return "\n".join(lines)

    def has_prompt(self) -> bool:
        """Check if the ']' BASIC prompt is visible on screen."""
        for line in self.get_text().split("\n"):
            if line.strip().startswith("]"):
                return True
        return False

    def count_prompts(self) -> int:
        """Count lines starting with ']' prompt."""
        count = 0
        for line in self.get_text().split("\n"):
            if line.strip().startswith("]"):
                count += 1
        return count

    def _mount(self, mem: ObservableMemory) -> None:
        mem.subscribe_to_read([0xC050], self.txtclr)
        mem.subscribe_to_read([0xC051], self.txtset)
        mem.subscribe_to_read([0xC052], self.mixclr)
        mem.subscribe_to_read([0xC053], self.mixset)
        mem.subscribe_to_read([0xC054], self.lowscr)
        mem.subscribe_to_read([0xC055], self.hiscr)
        mem.subscribe_to_read([0xC056], self.lores)
        mem.subscribe_to_read([0xC057], self.hires)
        mem.subscribe_to_write(range(0x400, 0xC00), self.update)
        mem.subscribe_to_write(range(0x2000, 0x6000), self.update)
