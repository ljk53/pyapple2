"""Pygame-backed mock of Pythonista's scene module.

Faithful shim — no device-specific layout logic here.
All adaptation belongs in the business layer.
"""

from __future__ import annotations

import pygame
from pygame import _freetype as _ft

_MOCK = True

# Font path for macOS (fallback to default if missing)
_FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"


class _DrawContext:
    def __init__(self):
        self.surface: pygame.Surface | None = None
        self.fill_color: tuple[int, int, int] = (0, 0, 0)
        self.tint_color: tuple[int, int, int] = (0, 0, 0)
        self.window_height: int = 0


_ctx = _DrawContext()
_font_cache: dict[tuple[str, int], _ft.Font] = {}
_ft_inited = False


def _c(r: float, g: float, b: float) -> tuple[int, int, int]:
    """Convert 0.0-1.0 color to 0-255."""
    return (int(r * 255), int(g * 255), int(b * 255))


def _to_rect(x: float, y: float, w: float, h: float) -> tuple[int, int, int, int]:
    """Convert scene rect (y-up origin) to pygame rect (y-down origin)."""
    return (int(x), int(_ctx.window_height - y - h), int(w), int(h))


def _to_point(x: float, y: float) -> tuple[int, int]:
    """Convert scene point to pygame point."""
    return (int(x), int(_ctx.window_height - y))


# --- Data types ---


class Point:
    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y

    def __iter__(self):
        return iter((self.x, self.y))

    def __getitem__(self, index: int):
        return (self.x, self.y)[index]

    def __repr__(self):
        return f"Point({self.x}, {self.y})"


class Size:
    def __init__(self, w: float = 0, h: float = 0):
        self.w = w
        self.h = h

    def __iter__(self):
        return iter((self.w, self.h))

    def __getitem__(self, index: int):
        return (self.w, self.h)[index]

    def __repr__(self):
        return f"Size({self.w}, {self.h})"


class Rect:
    def __init__(self, x: float = 0, y: float = 0, w: float = 0, h: float = 0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def center(self) -> Point:
        return Point(self.x + self.w / 2, self.y + self.h / 2)

    def __contains__(self, point) -> bool:
        return self.x <= point.x <= self.x + self.w and self.y <= point.y <= self.y + self.h

    def __iter__(self):
        return iter((self.x, self.y, self.w, self.h))

    def __repr__(self):
        return f"Rect({self.x}, {self.y}, {self.w}, {self.h})"


class Touch:
    def __init__(self, touch_id: int, location: Point):
        self.touch_id = touch_id
        self.location = location


# --- Drawing functions ---


def fill(r: float, g: float, b: float) -> None:
    _ctx.fill_color = _c(r, g, b)


def rect(x: float, y: float, w: float, h: float) -> None:
    if _ctx.surface and w > 0 and h > 0:
        pygame.draw.rect(_ctx.surface, _ctx.fill_color, _to_rect(x, y, w, h))


def ellipse(x: float, y: float, w: float, h: float) -> None:
    if _ctx.surface and w > 0 and h > 0:
        pygame.draw.ellipse(_ctx.surface, _ctx.fill_color, _to_rect(x, y, w, h))


def tint(r: float, g: float, b: float) -> None:
    _ctx.tint_color = _c(r, g, b)


def text(s: str, font_name: str = "Arial", font_size: float = 16, x: float = 0, y: float = 0) -> None:
    if not _ctx.surface or not s:
        return
    global _ft_inited
    if not _ft_inited:
        _ft.init()
        _ft_inited = True
    key = (font_name, int(font_size))
    if key not in _font_cache:
        import os

        path = _FONT_PATH if os.path.exists(_FONT_PATH) else None
        _font_cache[key] = _ft.Font(path, font_size)
    font = _font_cache[key]
    rendered, _ = font.render(s, _ctx.tint_color)
    px, py = _to_point(x, y)
    text_rect = rendered.get_rect(center=(px, py))
    _ctx.surface.blit(rendered, text_rect)


# --- Scene classes ---


class Scene:
    def __init__(self):
        self.size: Size = Size(0, 0)

    def setup(self) -> None:
        pass

    def draw(self) -> None:
        pass

    def touch_began(self, touch: Touch) -> None:
        pass

    def touch_moved(self, touch: Touch) -> None:
        pass

    def touch_ended(self, touch: Touch) -> None:
        pass


class SceneView:
    def __init__(self):
        self.scene: Scene | None = None
        self._subviews: list = []
        self.frame: tuple[float, float, float, float] = (0, 0, 414, 896)

    def add_subview(self, view) -> None:
        self._subviews.append(view)

    def present(self, style: str = "") -> None:
        pygame.init()
        w = int(self.frame[2])
        h = int(self.frame[3])
        _ctx.surface = pygame.display.set_mode((w, h))
        _ctx.window_height = h
        pygame.display.set_caption("ApplePy (iOS)")

        # Keep mock ui.get_screen_size() in sync
        import ui as _ui_mod

        _ui_mod._screen_size = (w, h)

        if self.scene:
            self.scene.size = Size(w, h)
            self.scene.setup()


def _mouse_to_scene(pos: tuple[int, int]) -> Point:
    """Convert pygame mouse position to scene coordinates."""
    mx, my = pos
    return Point(mx, _ctx.window_height - my)
