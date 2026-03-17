"""Centralized layout calculations for iOS frontend.

All positions are in y-down (screen/pygame) coordinates.
Scene y-up conversion happens at draw time in each component.
"""

from __future__ import annotations

SAFE_AREA_TOP = 44  # iPhone X family notch / dynamic island
DISPLAY_ASPECT = 384 / 560  # Apple II 2x-scaled bitmap aspect ratio

# Keyboard sizing constants — must stay in sync with keyboard_ios.build_layouts
_KBD_BTN_H = 95 * 0.42  # button height (constant, independent of scale)
_KBD_BASE_ROW_W = 363.09  # from keyboard_ios._BASE_ROW_W


def _kbd_content_height(screen_w: int) -> int:
    """Compute keyboard content height including toolbar row.

    5 rows of buttons (3 key rows + bottom row + toolbar) with 6 padding gaps.
    """
    kbd_scale = screen_w * 0.97 / _KBD_BASE_ROW_W
    btnpad = 12 * 0.42 * kbd_scale
    return round(btnpad * 6 + _KBD_BTN_H * 5)


def compute_layout(screen_w: int, screen_h: int) -> dict[str, tuple[int, ...]]:
    """Compute all UI element positions in y-down pixel coordinates.

    Returns dict with keys: display, registers, heatmap, keyboard_top, screen.
    Each value is a tuple of (x, y, w, h) or a single int.

    Layout strategy: pack all elements tightly (4px gaps) and align the
    stack to the bottom of the screen.  Any leftover space appears above
    the display, between the safe-area and the Apple II screen.
    """
    GAP = 4
    BOTTOM_MARGIN = 30

    display_h = round(screen_w * DISPLAY_ASPECT)
    reg_h = 28
    kbd_h = _kbd_content_height(screen_w)

    # Bottom-align: keyboard sits just above bottom margin
    kbd_top = screen_h - BOTTOM_MARGIN - kbd_h

    # Compute heatmap size from remaining space above keyboard
    fixed = display_h + GAP + reg_h + GAP + GAP
    heatmap_avail = kbd_top - GAP - SAFE_AREA_TOP - fixed
    heatmap_size = min(256, max(64, heatmap_avail), screen_w - 20)

    # Pack upward from keyboard
    heatmap_bottom = kbd_top - GAP
    heatmap_top = heatmap_bottom - heatmap_size
    reg_bottom = heatmap_top - GAP
    reg_top = reg_bottom - reg_h
    display_bottom = reg_top - GAP
    display_top = display_bottom - display_h

    heatmap_x = (screen_w - heatmap_size) // 2

    return {
        "display": (0, display_top, screen_w, display_h),
        "registers": (0, reg_top, screen_w, reg_h),
        "heatmap": (heatmap_x, heatmap_top, heatmap_size, heatmap_size),
        "keyboard_top": kbd_top,
        "screen": (screen_w, screen_h),
    }
