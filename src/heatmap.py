"""Memory activity heatmap renderer for the iOS frontend.

Renders a 256x256 pixel image where each pixel represents one byte of
the Apple II 64K address space.  Address 0xAABB maps to pixel (col=BB, row=AA).

RGB channels encode activity type:
  - Red   = write intensity
  - Green = execute (PC) intensity
  - Blue  = read intensity

Mixed colors: magenta = read+write, yellow = write+execute,
cyan = read+execute, white = all three.

Exponential decay gives ~3.5s half-life at 3Hz update rate.

Grid lines are initialized once and never overwritten by activity data,
eliminating flicker:
  - Horizontal at 4K page boundaries (every 16 rows)
  - Vertical at $40 byte intervals (every 64 columns)

Labels are drawn at render time in the margins surrounding the heatmap:
  - Left: 16 page labels ($0-$F)
  - Top: 4 column offset labels (00, 40, 80, C0)

Supports two rendering backends:
  - pygame (mock): ``draw_mock()`` blits a scaled surface with labels
  - Pythonista:    ``draw_pythonista()`` converts via PIL -> PNG -> ui.Image
"""

from __future__ import annotations

_HEATMAP_SIZE = 256  # 256x256 = 65536 pixels = 64K addresses
_DECAY_NUM = 15  # decay factor numerator   (15/16 = 0.9375)
_DECAY_DEN = 16  # decay factor denominator
_GRID_COLOR = (48, 48, 48)  # dark gray for grid lines

# Amplification — raw counts are small (esp. for sparse/sampled data).
# Write/Execute use <<6 (x64): 1->64, 4->255.
# Reads use a higher floor (192) because Apple II data reads are extremely
# sparse (1 byte at a time in the monitor) and need to stand out.
_AMP = 6  # shift for write/execute channels
_READ_FLOOR = 192  # minimum brightness for any non-zero data read

# Grid positions — initialized once, never overwritten by activity.
_GRID_ROWS = frozenset(range(16, 256, 16))  # 4K page boundaries
_GRID_COLS = frozenset(range(64, 256, 64))  # $40 byte intervals

# Label rendering
_LABEL_MARGIN_LEFT = 22  # pixels for row labels
_LABEL_MARGIN_TOP = 12  # pixels for column labels
_LABEL_COLOR = (160, 160, 160)
_LABEL_FONT_SIZE = 9
_LABEL_FONT_NAME = "Menlo"

# Page labels (left margin) and column labels (top margin)
_PAGE_LABELS = [f"${p:X}" for p in range(16)]
_COL_LABELS = [(0, "00"), (64, "40"), (128, "80"), (192, "C0")]


class HeatmapRenderer:
    """Converts 64K activity counts (R/W/X) into a coloured pixel buffer."""

    def __init__(self) -> None:
        self._pixels: bytearray = bytearray(_HEATMAP_SIZE * _HEATMAP_SIZE * 3)
        # Decay accumulators — persistent intensity per channel per address
        self._accum_r: list[int] = [0] * 65536
        self._accum_g: list[int] = [0] * 65536
        self._accum_b: list[int] = [0] * 65536
        self._init_grid()

    def _init_grid(self) -> None:
        """Draw grid lines into pixel buffer once.  update() skips these."""
        gr, gg, gb = _GRID_COLOR
        for addr in range(65536):
            row = addr >> 8
            col = addr & 0xFF
            if row in _GRID_ROWS or col in _GRID_COLS:
                off = addr * 3
                self._pixels[off] = gr
                self._pixels[off + 1] = gg
                self._pixels[off + 2] = gb

    def update(
        self,
        read_counts: bytearray,
        write_counts: bytearray,
        exec_counts: bytearray,
    ) -> None:
        """Decay accumulators then blend in new activity, render to pixels.

        Grid addresses are skipped — their pixels remain as initialized.
        Reads at addresses where execution occurred this period are
        instruction fetches, not data reads — suppress them so the B
        channel shows only true data-read activity.
        """
        ar = self._accum_r
        ag = self._accum_g
        ab = self._accum_b
        pixels = self._pixels
        dn = _DECAY_NUM
        dd = _DECAY_DEN
        amp = _AMP
        grid_rows = _GRID_ROWS
        grid_cols = _GRID_COLS

        for addr in range(65536):
            row = addr >> 8
            col = addr & 0xFF
            if row in grid_rows or col in grid_cols:
                continue

            # Reads at executed addresses are instruction fetches -> suppress
            rc = read_counts[addr]
            if rc and exec_counts[addr]:
                rc = 0

            # Channel mapping: R=write, G=execute, B=read
            r_new = min(255, write_counts[addr] << amp)
            g_new = min(255, exec_counts[addr] << amp)
            b_new = min(255, max(_READ_FLOOR, rc << amp)) if rc else 0

            # Exponential decay + amplified new activity
            r = min(255, ar[addr] * dn // dd + r_new)
            g = min(255, ag[addr] * dn // dd + g_new)
            b = min(255, ab[addr] * dn // dd + b_new)
            ar[addr] = r
            ag[addr] = g
            ab[addr] = b

            off = addr * 3
            pixels[off] = r
            pixels[off + 1] = g
            pixels[off + 2] = b

    # -- Mock (pygame) backend ------------------------------------------------

    def draw_mock(self, surface: object, x: int, y: int, w: int, h: int) -> None:
        """Blit heatmap onto a pygame surface at (x, y, w, h) with labels."""
        import pygame

        # Black background behind entire heatmap area (margins + image)
        pygame.draw.rect(surface, (0, 0, 0), (x, y, w, h))  # type: ignore[union-attr]

        lm = _LABEL_MARGIN_LEFT
        tm = _LABEL_MARGIN_TOP
        img_size = min(w - lm, h - tm)

        # Heatmap image
        img = pygame.image.frombuffer(
            bytes(self._pixels), (_HEATMAP_SIZE, _HEATMAP_SIZE), "RGB"
        )
        scaled = pygame.transform.scale(img, (img_size, img_size))
        surface.blit(scaled, (x + lm, y + tm))  # type: ignore[union-attr]

        # Labels
        font = _get_mock_font()
        if font is None:
            return
        scale = img_size / _HEATMAP_SIZE

        # Row labels: 16 page addresses along left margin
        for page in range(16):
            label_y = y + tm + int(page * 16 * scale)
            rendered = font.render(_PAGE_LABELS[page], True, _LABEL_COLOR)
            surface.blit(rendered, (x, label_y))  # type: ignore[union-attr]

        # Column labels: byte offsets along top margin
        for col_addr, label_text in _COL_LABELS:
            label_x = x + lm + int(col_addr * scale)
            rendered = font.render(label_text, True, _LABEL_COLOR)
            surface.blit(rendered, (label_x, y))  # type: ignore[union-attr]

    # -- Pythonista backend ---------------------------------------------------

    def draw_pythonista(self, x: float, y: float, w: float, h: float) -> None:
        """Draw heatmap image via PIL, labels via native ui.draw_string."""
        import io

        import ui  # type: ignore[import-not-found]
        from PIL import Image as PILImage  # type: ignore[import-not-found]

        lm = _LABEL_MARGIN_LEFT
        tm = _LABEL_MARGIN_TOP
        img_w = w - lm
        img_h = h - tm

        # Heatmap image (offset by label margins)
        pil_img = PILImage.frombytes(
            "RGB", (_HEATMAP_SIZE, _HEATMAP_SIZE), bytes(self._pixels)
        )
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG", compress_level=1)
        ui_img = ui.Image.from_data(buf.getvalue())
        ui_img.draw(x + lm, y + tm, img_w, img_h)

        # Labels using native Pythonista text rendering
        scale_x = img_w / _HEATMAP_SIZE
        scale_y = img_h / _HEATMAP_SIZE
        label_font = (_LABEL_FONT_NAME, _LABEL_FONT_SIZE)
        label_color = "#A0A0A0"

        for page in range(16):
            label_y = y + tm + page * 16 * scale_y
            ui.draw_string(
                _PAGE_LABELS[page],
                rect=(x, label_y, lm - 2, 14),
                font=label_font,
                color=label_color,
            )

        for col_addr, label_text in _COL_LABELS:
            label_x = x + lm + col_addr * scale_x
            ui.draw_string(
                label_text,
                rect=(label_x, y, 30, tm),
                font=label_font,
                color=label_color,
            )


# -- Font helpers (cached) ---------------------------------------------------

_mock_font_cache: object | None = None


def _get_mock_font() -> object | None:
    """Get a cached pygame font for label rendering."""
    global _mock_font_cache
    if _mock_font_cache is not None:
        return _mock_font_cache
    try:
        import pygame.font

        if not pygame.font.get_init():
            pygame.font.init()
        _mock_font_cache = pygame.font.SysFont(_LABEL_FONT_NAME, _LABEL_FONT_SIZE)
    except Exception:
        try:
            _mock_font_cache = pygame.font.SysFont("monospace", _LABEL_FONT_SIZE)
        except Exception:
            return None
    return _mock_font_cache
