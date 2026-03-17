"""Pygame-backed mock of Pythonista's ui module."""

from __future__ import annotations

_MOCK = True

ALIGN_CENTER = 1

# Screen size — set by SceneView.present()
_screen_size: tuple[float, float] = (414, 896)


def get_screen_size() -> tuple[float, float]:
    return _screen_size


class View:

    def __init__(self, *args, frame=None, background_color=None, **kwargs):
        self.frame = frame or (0, 0, 0, 0)
        self.background_color = background_color
        self.subviews = []
        self._needs_display = False

    @property
    def width(self) -> float:
        return self.frame[2] if self.frame else 0

    @property
    def height(self) -> float:
        return self.frame[3] if self.frame else 0

    def draw(self):
        pass

    def set_needs_display(self):
        self._needs_display = True

    def add_subview(self, v):
        self.subviews.append(v)


def draw_string(string="", font=None, alignment=0):
    pass
