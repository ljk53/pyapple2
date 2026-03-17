from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from runtime import Runtime

try:
    import ui
except ImportError:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pythonista_mock"))
    import ui  # type: ignore

_MOCK: bool = getattr(ui, "_MOCK", False)

from display_bitmap import BitmapDisplay, WIDTH, HEIGHT

if _MOCK:
    import pygame


class Display(ui.View):

    def __init__(self, runtime: Runtime, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._bitmap: BitmapDisplay = BitmapDisplay(runtime.memory._mem)
        self._mount_write_switches(runtime)

    def _mount_write_switches(self, runtime: Runtime) -> None:
        """Subscribe to soft-switch writes (STA-based mode changes).

        BitmapDisplay._mount() already handles read subscriptions and
        memory write subscriptions. This adds write subscriptions for
        soft switches so STA $C050-$C057 works (matching display_pygame).
        """
        for addr, method in [
            (0xC050, self._bitmap.txtclr),
            (0xC051, self._bitmap.txtset),
            (0xC052, self._bitmap.mixclr),
            (0xC053, self._bitmap.mixset),
            (0xC054, self._bitmap.lowscr),
            (0xC055, self._bitmap.hiscr),
            (0xC056, self._bitmap.lores),
            (0xC057, self._bitmap.hires),
        ]:
            runtime.subscribe_to_write([addr], lambda a, v, m=method: m(a))

    def draw(self) -> None:
        if _MOCK:
            surface = pygame.display.get_surface()
            if surface:
                img = pygame.image.frombuffer(bytes(self._bitmap.pixels), (WIDTH, HEIGHT), "RGB")
                sw = surface.get_width()
                sh = round(HEIGHT * sw / WIDTH)
                scaled = pygame.transform.smoothscale(img, (sw, sh))
                surface.blit(scaled, (int(self.frame[0]), int(self.frame[1])))
        else:
            # Pythonista: pixels → PIL → PNG → ui.Image → draw
            import io
            from PIL import Image as PILImage

            pil_img = PILImage.frombytes("RGB", (WIDTH, HEIGHT), bytes(self._bitmap.pixels))
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG", compress_level=1)
            ui_img = ui.Image.from_data(buf.getvalue())
            ui_img.draw(0, 0, self.width, self.height)
