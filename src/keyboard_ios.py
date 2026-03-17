# Original Source: https://github.com/JadedTuna/scene-keyboard

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import scene as _scene
    from runtime import Runtime

try:
    from scene import *
except ImportError:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pythonista_mock"))
    from scene import *  # type: ignore

from keyboard import KeyboardBase

DSHADE_COLOUR: tuple[float, float, float] = (0.5, 0.5, 0.5)

BDBG: tuple[float, float, float] = (1.0, 1.0, 1.0)  # Button Default BackGround
BPBG: tuple[float, float, float] = (0.8, 0.8, 0.8)  # Button Pressed BackGround

SDBG: tuple[float, float, float] = (0.73, 0.74, 0.76)  # Special button Default BackGround
SPBG: tuple[float, float, float] = (1.0, 1.0, 1.0)  # Special button Pressed BackGround

TDFG: tuple[float, float, float] = (0.0, 0.0, 0.0)  # Text Default ForeGround
TPFG: tuple[float, float, float] = (0.0, 0.0, 0.0)  # Text Pressed ForeGround

RDBG: tuple[float, float, float] = (0.80, 0.20, 0.20)  # Reset Default BackGround
RPBG: tuple[float, float, float] = (0.60, 0.10, 0.10)  # Reset Pressed BackGround
RWFG: tuple[float, float, float] = (1.0, 1.0, 1.0)  # Reset text White ForeGround

CDBG: tuple[float, float, float] = (0.20, 0.50, 0.80)  # CTRL active bg (blue)
CPBG: tuple[float, float, float] = (0.15, 0.40, 0.70)  # CTRL active pressed

SPDG: tuple[float, float, float] = (0.20, 0.65, 0.30)  # Speed throttled bg (green)
SPPG: tuple[float, float, float] = (0.15, 0.50, 0.25)  # Speed throttled pressed


def cylinder(x: float = 0, y: float = 0, w: float = 0, h: float = 0, r: float = 0) -> None:
    rect(x + h / 2, y, w - h, h)
    ellipse(x, y, h, h)
    ellipse(x + w - h, y, h, h)


def round_rect(x: float, y: float, w: float, h: float, r: float = 0) -> None:
    if r <= 0:
        rect(x, y, w, h)
    elif r >= h:
        cylinder(x, y, w, h)
    else:
        d = r * 2
        rect(x + r, y, w - d, h)
        rect(x, y + r, w, h - d)
        ellipse(x, y, d, d)
        ellipse(x, y + h - d, d, d)
        ellipse(x + w - d, y, d, d)
        ellipse(x + w - d, y + h - d, d, d)


def shaded_rect(
    x: float,
    y: float,
    w: float,
    h: float,
    colour: tuple[float, float, float],
    shade_colour: tuple[float, float, float],
    border: float = 1,
) -> None:
    r = 5  # Default button radius
    fill(*shade_colour)
    round_rect(x, y - border, w, h, r)
    fill(*colour)
    round_rect(x, y, w, h, r)


class TextButton(object):
    def __init__(
        self,
        text: str | None,
        value: str,
        pos: _scene.Point,
        size: _scene.Size,
        bgcolours: list[tuple[float, float, float]],
        fgcolours: list[tuple[float, float, float]],
        fontfamily: str,
        fontsize: float,
        action: Callable[[str], None] | None,
        id: int,
    ) -> None:
        self.size: _scene.Size = size
        self.bounds: _scene.Rect = Rect(pos.x, pos.y, *size)

        self.dbg: tuple[float, float, float]
        self.pbg: tuple[float, float, float]
        self.dbg, self.pbg = bgcolours  # Default bg and pressed bg
        self.dfg: tuple[float, float, float]
        self.pfg: tuple[float, float, float]
        self.dfg, self.pfg = fgcolours  # Default fg and pressed fg
        self.shade_colour: tuple[float, float, float] = DSHADE_COLOUR
        self.drawbg: tuple[float, float, float] = self.dbg
        self.drawfg: tuple[float, float, float] = self.dfg

        self.drawfunc: Callable[[float, float, float, float], None] = lambda x, y, w, h: shaded_rect(
            x, y, w, h, self.drawbg, self.shade_colour
        )

        self.text: str | None = text
        self.fontfam: str = fontfamily
        self.fontsize: float = fontsize
        self.value: str = value

        self.touch_id: int | None = None
        self.parent: KeyboardView | None = None
        self.action: Callable[[str], None] | None = action
        self.button_id: int = id

    def init(self, parent: KeyboardView) -> None:
        """
        Init a button, give it a parent keyboard!
        """
        self.parent = parent
        self.bounds = Rect(
            self.bounds.x + self.parent.bounds.x, self.bounds.y + self.parent.bounds.y, self.bounds.w, self.bounds.h
        )
        self.textpos: _scene.Point = self.bounds.center()
        self.action = self.action if self.action else parent.daction

    def draw(self) -> None:
        # This is needed incase some other drawing functions is used
        fill(*self.drawbg)
        self.drawfunc(*self.bounds)
        x, y = self.textpos
        tint(*self.drawfg)
        if self.text:
            text(self.text, self.fontfam, self.fontsize, x, y)

    def hit_test(self, point: _scene.Point) -> bool:
        return point in self.bounds

    def touch_began(self, touch: _scene.Touch) -> None:
        if not self.touch_id:
            self.touch_id = touch.touch_id
            self.drawbg = self.pbg
            self.drawfg = self.pfg

    def touch_moved(self, touch: _scene.Touch) -> None:
        if touch.touch_id == self.touch_id:
            if touch.location in self.bounds:
                self.drawbg = self.pbg
                self.drawfg = self.pfg
            else:
                self.drawbg = self.dbg
                self.drawfg = self.dfg

    def touch_ended(self, touch: _scene.Touch) -> None:
        if touch.touch_id == self.touch_id:
            self.touch_id = None
            self.drawbg = self.dbg
            self.drawfg = self.dfg
            if touch.location in self.bounds:
                self.clicked()

    def clicked(self) -> None:
        if self.action:
            self.action(self.value)


class Layout(object):
    """
    Represents a layout for keyboard.
    """

    def __init__(self) -> None:
        self.keyboard: KeyboardView | None = None
        self.buttons: list[TextButton] = []
        self.ids: list[int] = []
        self.daction: Callable[[str], None] | None = None
        self.dsize: _scene.Size = Size(10, 10)
        self._content_h: float | None = None

    def newID(self) -> int | None:
        """
        Returns a new, unused ID.
        """
        for id in self.ids:
            if not id + 1 in self.ids:
                return id + 1

    def setDefaultSize(self, size: _scene.Size | tuple[float, float]) -> None:
        if not isinstance(size, Size):
            size = Size(*size)
        self.dsize = size

    def addTextButton(
        self,
        text: str | None,
        value: str,
        pos: _scene.Point | tuple[float, float],
        size: _scene.Size | tuple[float, float] | None = None,
        bgcolours: list[tuple[float, float, float]] = [BDBG, BPBG],
        fgcolours: list[tuple[float, float, float]] = [TDFG, TPFG],
        fontfamily: str = "Arial",
        fontsize: float = 28,
        action: Callable[[str], None] | None = None,
        id: int = -1,
    ) -> None:
        if not size:
            size = self.dsize

        if not isinstance(pos, Point):
            pos = Point(*pos)
        if not isinstance(size, Size):
            size = Size(*size)

        if id == -1:
            id = self.newID()
        button = TextButton(text, value, pos, size, bgcolours, fgcolours, fontfamily, fontsize, action, id)
        self.buttons.append(button)

    def addSpecialTextButton(
        self,
        text: str | None,
        value: str,
        pos: _scene.Point | tuple[float, float],
        size: _scene.Size | tuple[float, float] | None = None,
        fontfamily: str = "Arial",
        fontsize: float = 28,
        action: Callable[[str], None] | None = None,
        id: int = -1,
    ) -> None:
        return self.addTextButton(text, value, pos, size, [SDBG, SPBG], [TDFG, TPFG], fontfamily, fontsize, action, id)

    def getButtonByID(self, id: int) -> TextButton | None:
        for button in self.buttons:
            if button.button_id == id:
                return button

    def init(self, keyboard: KeyboardView) -> None:
        self.keyboard = keyboard
        self.daction = keyboard.daction
        for button in self.buttons:
            button.init(self.keyboard)

    def kbd_size(self) -> tuple[float, float]:
        if self._content_h is not None:
            return (self.keyboard.scrsize.w, self._content_h)
        return (self.keyboard.scrsize.w, self.keyboard.scrsize.h / 4.4)


TKEYS = (
    (
        ("Q", "Q"),
        ("W", "W"),
        ("E", "E"),
        ("R", "R"),
        ("T", "T"),
        ("Y", "Y"),
        ("U", "U"),
        ("I", "I"),
        ("O", "O"),
        ("P", "P"),
    ),
    (
        ("A", "A"),
        ("S", "S"),
        ("D", "D"),
        ("F", "F"),
        ("G", "G"),
        ("H", "H"),
        ("J", "J"),
        ("K", "K"),
        ("L", "L"),
    ),
    (
        ("Z", "Z"),
        ("X", "X"),
        ("C", "C"),
        ("V", "V"),
        ("B", "B"),
        ("N", "N"),
        ("M", "M"),
        (",", ","),
        (".", "."),
    ),
)

NKEYS = (
    (
        ("1", "1"),
        ("2", "2"),
        ("3", "3"),
        ("4", "4"),
        ("5", "5"),
        ("6", "6"),
        ("7", "7"),
        ("8", "8"),
        ("9", "9"),
        ("0", "0"),
    ),
    (
        ("-", "-"),
        ("/", "/"),
        (":", ":"),
        (";", ";"),
        ("(", "("),
        (")", ")"),
        ("$", "$"),
        ("&", "&"),
        ("@", "@"),
    ),
    (
        None,
        (".", "."),
        (",", ","),
        ("?", "?"),
        ("!", "!"),
        ("'", "'"),
        ('"', '"'),
    ),
)

SKEYS = (
    (
        ("#", "#"),
        ("+", "+"),
        ("=", "="),
        ("*", "*"),
        ("<", "<"),
        (">", ">"),
        ("[", "["),
        ("]", "]"),
        ("\\", "\\"),
        ("^", "^"),
    ),
    (
        ("%", "%"),
        ("_", "_"),
        ("!", "!"),
        ("?", "?"),
        ("@", "@"),
        ("&", "&"),
        ("$", "$"),
        ("'", "'"),
        ('"', '"'),
    ),
    (
        None,
        ("-", "-"),
        ("/", "/"),
        (":", ":"),
        (";", ";"),
        ("(", "("),
        (")", ")"),
        (",", ","),
        (".", "."),
    ),
)


# Q-P row width at scale=1 — used to compute scale from screen width
_BASE_ROW_W: float = (6.5 + (12 + 75) * 9 + 75) * 0.42  # ≈ 363.09


def build_layouts(kbd_scale: float) -> tuple[Layout, Layout, Layout, float]:
    """Build keyboard layouts sized for the given scale.

    Returns (letters_layout, numbers_layout, symbols_layout, row_width).
    """
    s = 0.42 * kbd_scale
    btnsize = Size(75 * s, 95 * s / kbd_scale)
    btnpad = 12 * s
    rowpad = [6.5 * s, 45 * s, 98 * s]
    fontsize = 14 * kbd_scale

    btnsize_return = (136 * s, btnsize[1])
    btnsize_spacebar = (btnsize[0] * 6 + btnpad * 5, btnsize[1])

    row_width = rowpad[0] + (btnpad + btnsize[0]) * 9 + btnsize[0]
    reset_y = btnpad * 5 + btnsize[1] * 4

    def add_buttons(layout: Layout, keys: tuple[Any, ...]) -> None:
        for row in range(3):
            for col, key in enumerate(keys[row]):
                if not key:
                    continue
                layout.addTextButton(
                    key[0],
                    key[1],
                    (rowpad[row] + (btnpad + btnsize[0]) * col, btnpad * (4 - row) + btnsize[1] * (3 - row)),
                    fontsize=fontsize,
                )

    tl = Layout()
    nl = Layout()
    sl = Layout()
    tl.setDefaultSize(btnsize)
    nl.setDefaultSize(btnsize)
    sl.setDefaultSize(btnsize)

    add_buttons(tl, TKEYS)
    add_buttons(nl, NKEYS)
    add_buttons(sl, SKEYS)

    # --- Bottom row: layout switch, spacebar, return ---
    # Letters: .?123 switches to numbers
    tl.addSpecialTextButton(
        ".?123", ".?123", (rowpad[0], btnpad), (btnsize[0] * 1.5, btnsize[1]), "Arial", fontsize, id=5000
    )
    # Numbers: ABC switches to letters, #+= switches to symbols
    nl.addSpecialTextButton(
        "ABC", "ABC", (rowpad[0], btnpad), (btnsize[0] * 1.5, btnsize[1]), "Arial", fontsize, id=5000
    )
    nl.addSpecialTextButton(
        "#+=", "#+=", (rowpad[0], btnpad * 2 + btnsize[1]), (btnsize[0] * 1.5, btnsize[1]), "Arial", fontsize, id=5001
    )
    # Symbols: ABC switches to letters, 123 switches to numbers
    sl.addSpecialTextButton(
        "ABC", "ABC", (rowpad[0], btnpad), (btnsize[0] * 1.5, btnsize[1]), "Arial", fontsize, id=5000
    )
    sl.addSpecialTextButton(
        "123", "123", (rowpad[0], btnpad * 2 + btnsize[1]), (btnsize[0] * 1.5, btnsize[1]), "Arial", fontsize, id=5001
    )

    for layout in [tl, nl, sl]:
        layout.addTextButton(None, " ", (rowpad[0] + (btnpad + btnsize[0]) * 2, btnpad), btnsize_spacebar)
        layout.addSpecialTextButton(
            "return", "\n", (rowpad[0] + (btnpad + btnsize[0]) * 8, btnpad), btnsize_return, fontsize=fontsize
        )

    # --- Toolbar row: ESC, CTRL, ←, RESET, →, FAST/1MHz ---
    toolbar_fontsize = fontsize * 0.85
    kw = btnsize[0]  # one key width
    kh = btnsize[1]
    x = rowpad[0]

    def _add_toolbar(layout: Layout) -> None:
        cx = x
        # ESC — 1.5 key widths
        w_esc = kw * 1.5 + btnpad * 0.5
        layout.addTextButton(
            "ESC", "\x1b", (cx, reset_y), (w_esc, kh),
            bgcolours=[SDBG, SPBG], fgcolours=[TDFG, TPFG],
            fontsize=toolbar_fontsize, id=6001,
        )
        cx += w_esc + btnpad
        # CTRL — 1.5 key widths
        w_ctrl = kw * 1.5 + btnpad * 0.5
        layout.addSpecialTextButton(
            "CTRL", "CTRL", (cx, reset_y), (w_ctrl, kh),
            fontsize=toolbar_fontsize, id=6002,
        )
        cx += w_ctrl + btnpad
        # ← — 1 key width
        layout.addTextButton(
            "\u2190", "\x08", (cx, reset_y), (kw, kh),
            bgcolours=[SDBG, SPBG], fgcolours=[TDFG, TPFG],
            fontsize=toolbar_fontsize, id=6003,
        )
        cx += kw + btnpad
        # RESET — 2.5 key widths
        w_reset = kw * 2.5 + btnpad * 1.5
        layout.addTextButton(
            "RESET", "RESET", (cx, reset_y), (w_reset, kh),
            bgcolours=[RDBG, RPBG], fgcolours=[RWFG, RWFG],
            fontsize=toolbar_fontsize, id=6000,
        )
        cx += w_reset + btnpad
        # → — 1 key width
        layout.addTextButton(
            "\u2192", "\x15", (cx, reset_y), (kw, kh),
            bgcolours=[SDBG, SPBG], fgcolours=[TDFG, TPFG],
            fontsize=toolbar_fontsize, id=6004,
        )
        cx += kw + btnpad
        # FAST/1MHz — 2 key widths
        w_speed = kw * 2 + btnpad
        layout.addSpecialTextButton(
            "FAST", "SPEED", (cx, reset_y), (w_speed, kh),
            fontsize=toolbar_fontsize, id=6005,
        )

    # Total keyboard content height including toolbar row
    total_kbd_h = reset_y + kh + btnpad
    for layout in [tl, nl, sl]:
        _add_toolbar(layout)
        layout._content_h = total_kbd_h

    return tl, nl, sl, row_width


class KeyboardView(object):
    def __init__(self, scrsize: _scene.Size, pos: _scene.Point = Point(0, 30)) -> None:
        self.size: tuple[float, float] = (scrsize.w, scrsize.h)
        self.bounds: _scene.Rect = Rect(pos.x, pos.y, *self.size)
        self.bg: tuple[float, float, float] = (0.8118, 0.8235, 0.8353)
        self.layouts: dict[str, Layout] = {}
        self.clayout: str | None = None
        self.daction: Callable[[str], None] = lambda text: None
        self.scrsize: _scene.Size = scrsize

    def addLayout(self, name: str, layout: Layout) -> None:
        self.layouts[name] = layout
        self.layouts[name].init(self)

    def setLayout(self, name: str, layout: Layout | None = None) -> None:
        if layout:
            self.addLayout(name, layout)
        self.clayout = name
        self.size = self.layouts[self.clayout].kbd_size()
        self.bounds.w, self.bounds.h = self.size

    def setDefaultAction(self, action: Callable[[str], None]) -> None:
        self.daction = action

    def draw(self) -> None:
        fill(*self.bg)
        rect(*self.bounds)
        for button in self.layouts[self.clayout].buttons:
            button.draw()

    def touch_began(self, touch: _scene.Touch) -> None:
        for button in self.layouts[self.clayout].buttons:
            if touch.location in button.bounds:
                button.touch_began(touch)
                return

    def touch_moved(self, touch: _scene.Touch) -> None:
        for button in self.layouts[self.clayout].buttons:
            button.touch_moved(touch)

    def touch_ended(self, touch: _scene.Touch) -> None:
        for button in self.layouts[self.clayout].buttons:
            if button.touch_id == touch.touch_id:
                button.touch_ended(touch)
                return

    def init(self) -> None:
        # Letters: .?123 → numbers
        btn_123: TextButton | None = self.layouts["letters-landscape"].getButtonByID(5000)
        btn_123.action = lambda text: self.setLayout("numbers-landscape")

        # Numbers: ABC → letters, #+= → symbols
        btn_abc_n: TextButton | None = self.layouts["numbers-landscape"].getButtonByID(5000)
        btn_abc_n.action = lambda text: self.setLayout("letters-landscape")
        btn_sym: TextButton | None = self.layouts["numbers-landscape"].getButtonByID(5001)
        btn_sym.action = lambda text: self.setLayout("symbols-landscape")

        # Symbols: ABC → letters, 123 → numbers
        btn_abc_s: TextButton | None = self.layouts["symbols-landscape"].getButtonByID(5000)
        btn_abc_s.action = lambda text: self.setLayout("letters-landscape")
        btn_num: TextButton | None = self.layouts["symbols-landscape"].getButtonByID(5001)
        btn_num.action = lambda text: self.setLayout("numbers-landscape")


_ALL_LAYOUTS = ("letters-landscape", "numbers-landscape", "symbols-landscape")


class Keyboard(Scene, KeyboardBase):

    def __init__(self, runtime: Runtime) -> None:
        Scene.__init__(self)
        KeyboardBase.__init__(self, runtime)
        self._runtime: Runtime = runtime
        self._extra_drawables: list[Callable[[], None]] = []
        self._ctrl_active: bool = False

    def add_drawable(self, fn: Callable[[], None]) -> None:
        """Register an extra draw callback invoked each frame."""
        self._extra_drawables.append(fn)

    def pressed(self, value: str) -> None:
        if self._ctrl_active and value and value[0].isalpha():
            ctrl_code = chr(ord(value[0].upper()) & 0x1F)
            self._set_ctrl(False)
            KeyboardBase.pressed(self, ctrl_code)
        else:
            if self._ctrl_active:
                self._set_ctrl(False)
            KeyboardBase.pressed(self, value)

    # --- CTRL toggle ---

    def _toggle_ctrl(self, _value: str) -> None:
        self._set_ctrl(not self._ctrl_active)

    def _set_ctrl(self, active: bool) -> None:
        self._ctrl_active = active
        bg = CDBG if active else SDBG
        pbg = CPBG if active else SPBG
        for name in _ALL_LAYOUTS:
            btn: TextButton | None = self.keyboard.layouts[name].getButtonByID(6002)
            if btn:
                btn.dbg = bg
                btn.pbg = pbg
                btn.drawbg = bg

    # --- Speed toggle ---

    def _toggle_speed(self, _value: str) -> None:
        throttled = self._runtime.toggle_throttle()
        self._update_speed_buttons(throttled)

    def _update_speed_buttons(self, throttled: bool) -> None:
        label = "1MHz" if throttled else "FAST"
        bg = SPDG if throttled else SDBG
        pbg = SPPG if throttled else SPBG
        for name in _ALL_LAYOUTS:
            btn: TextButton | None = self.keyboard.layouts[name].getButtonByID(6005)
            if btn:
                btn.text = label
                btn.dbg = bg
                btn.pbg = pbg
                btn.drawbg = bg

    def setup(self) -> None:
        # Compute scale to fit keyboard to ~97% of screen width
        kbd_scale = self.size.w * 0.97 / _BASE_ROW_W
        tl, nl, sl, row_width = build_layouts(kbd_scale)

        pos_x = max(0, (self.size.w - row_width) / 2)
        self.keyboard: KeyboardView = KeyboardView(self.size, pos=Point(pos_x, 30))
        self.keyboard.setDefaultAction(self.pressed)
        self.keyboard.setLayout("letters-landscape", tl)
        self.keyboard.addLayout("numbers-landscape", nl)
        self.keyboard.addLayout("symbols-landscape", sl)
        self.keyboard.init()

        # Wire up toolbar buttons across all layouts
        for layout_name in _ALL_LAYOUTS:
            layout = self.keyboard.layouts[layout_name]
            # RESET
            btn: TextButton | None = layout.getButtonByID(6000)
            if btn:
                btn.action = lambda v: self._runtime.reset()
            # CTRL
            btn = layout.getButtonByID(6002)
            if btn:
                btn.action = self._toggle_ctrl
            # Speed
            btn = layout.getButtonByID(6005)
            if btn:
                btn.action = self._toggle_speed

        # Set initial speed button state
        self._update_speed_buttons(self._runtime.throttled)

    def draw(self) -> None:
        self.keyboard.draw()
        for fn in self._extra_drawables:
            fn()

    def touch_began(self, touch: _scene.Touch) -> None:
        self.keyboard.touch_began(touch)

    def touch_moved(self, touch: _scene.Touch) -> None:
        self.keyboard.touch_moved(touch)

    def touch_ended(self, touch: _scene.Touch) -> None:
        self.keyboard.touch_ended(touch)
