"""CPU register monitor panel for the iOS frontend.

Draws live CPU state (A, X, Y, SP, PC, flags, cycles) using scene
drawing primitives.  Works in both Pythonista and the pygame mock.

All public coordinates use y-down (screen) convention; conversion to
scene y-up happens internally at draw time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime import Runtime

try:
    from scene import fill, rect, tint, text
except ImportError:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pythonista_mock"))
    from scene import fill, rect, tint, text  # type: ignore


# Flag bit names in 6502 status register order (bit 7 -> bit 0)
_FLAGS = [
    ("sign_flag", "N"),
    ("overflow_flag", "V"),
    (None, "-"),  # unused bit, always 1
    ("break_flag", "B"),
    ("decimal_mode_flag", "D"),
    ("interrupt_disable_flag", "I"),
    ("zero_flag", "Z"),
    ("carry_flag", "C"),
]

# Monospace font: Menlo on iOS/macOS, fallback handled by mock
_FONT = "Menlo"


class MonitorPanel:
    """Renders CPU register state as text in the given screen region."""

    def __init__(self, runtime: Runtime) -> None:
        self._runtime: Runtime = runtime

    def draw(self, bounds_ydown: tuple[int, ...], window_height: int) -> None:
        """Draw the register panel.

        *bounds_ydown* is ``(x, y, w, h)`` in y-down screen coordinates.
        *window_height* is the total window/screen height (for y-up conversion).
        """
        bx, by, bw, bh = bounds_ydown
        # Convert to scene y-up: scene_y = window_height - ydown_bottom
        sy = window_height - by - bh

        # Background
        fill(0.10, 0.10, 0.13)
        rect(bx, sy, bw, bh)

        status = self._runtime.get_status()

        fontsize = max(10, bh * 0.55)

        tint(0.0, 0.78, 0.0)  # green phosphor
        a = status["accumulator"]
        xr = status["x_index"]
        yr = status["y_index"]
        sp = status["stack_pointer"]
        pc = status["program_counter"]

        flags = ""
        for name, letter in _FLAGS:
            if name is None:
                flags += "1"
            elif status[name]:
                flags += letter
            else:
                flags += "."

        line = f"A:{a:02X} X:{xr:02X} Y:{yr:02X} SP:{sp:02X} PC:{pc:04X} {flags}"
        text(line, _FONT, fontsize, bx + bw / 2, sy + bh * 0.5)
