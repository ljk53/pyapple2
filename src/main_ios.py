from __future__ import annotations

import argparse

try:
    import scene
except ImportError:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pythonista_mock"))
    import scene  # type: ignore

_MOCK: bool = getattr(scene, "_MOCK", False)

import ui  # available on both Pythonista (built-in) and mock (on path)
import options
from runtime import Runtime
from display_ios import Display
from keyboard_ios import Keyboard
from layout_ios import compute_layout
from monitor_panel import MonitorPanel
from heatmap import HeatmapRenderer

if _MOCK:
    import pygame


class HeatmapView(ui.View):
    """ui.View wrapper around HeatmapRenderer.

    Works on both Pythonista (framework calls draw() automatically)
    and mock (mock loop calls draw() explicitly).
    """

    def __init__(self, renderer: HeatmapRenderer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._renderer: HeatmapRenderer = renderer
        self.background_color = "black"

    def draw(self) -> None:
        if _MOCK:
            surface = pygame.display.get_surface()
            if surface:
                x, y, w, h = self.frame
                self._renderer.draw_mock(surface, int(x), int(y), int(w), int(h))
        else:
            self._renderer.draw_pythonista(0, 0, self.width, self.height)


class Main:

    def __init__(
        self, options: argparse.Namespace, runtime: Runtime, heatmap_view: HeatmapView
    ) -> None:
        self.display: Display = Display(runtime)
        self.keyboard: Keyboard = Keyboard(runtime)
        self.monitor: MonitorPanel = MonitorPanel(runtime)
        self.heatmap_view: HeatmapView = heatmap_view
        self.layout: dict = {}
        self.show()

    def show(self) -> None:
        v: scene.SceneView = scene.SceneView()
        v.scene = self.keyboard
        v.add_subview(self.display)
        v.add_subview(self.heatmap_view)
        if _MOCK:
            v.frame = (0, 0, 414, 896)  # iPhone XS Max portrait
        v.present("sheet")

        screen_w, screen_h = ui.get_screen_size()
        self.layout = compute_layout(int(screen_w), int(screen_h))
        self.display.frame = self.layout["display"]
        self.heatmap_view.frame = self.layout["heatmap"]

        # Register monitor as extra drawable in the keyboard scene
        # (scene.draw() is called every frame by both Pythonista and mock)
        self.keyboard.add_drawable(
            lambda: self.monitor.draw(self.layout["registers"], int(screen_h))
        )

    def run(self) -> None:
        self.display.set_needs_display()
        self.heatmap_view.set_needs_display()


class Looper:

    def __init__(self) -> None:
        self.options: argparse.Namespace = options.get_options()
        self.runtime: Runtime = Runtime(self.options)

        # Steps (instructions) per frame.  See main_pygame.py for details.
        self._steps_per_frame: int = 32768 if self.options.disk else 8192

        # Activity tracking for R/W/X heatmap
        self.runtime.enable_activity_tracking()
        self._heatmap: HeatmapRenderer = HeatmapRenderer()
        self._heatmap_view: HeatmapView = HeatmapView(self._heatmap)
        self._frame_count: int = 0

        self.main: Main = Main(self.options, self.runtime, self._heatmap_view)

    def _update_heatmap(self) -> None:
        """Fetch activity counts, feed to heatmap renderer, clear counters."""
        activity = self.runtime.get_activity()
        if activity is not None:
            rc, wc, ec = activity
            self._heatmap.update(rc, wc, ec)
            self.runtime.clear_activity()

    def start(self) -> None:
        if _MOCK:
            self._mock_loop()
        else:
            self._pythonista_loop()

    def _pythonista_loop(self) -> None:
        while True:
            self.runtime.run(self._steps_per_frame)
            self.main.run()

            # Update heatmap every 10 frames (~3 Hz)
            self._frame_count += 1
            if self._frame_count % 10 == 0:
                self._update_heatmap()

    def _mock_loop(self) -> None:
        clock = pygame.time.Clock()
        screenshot_path = getattr(self.options, "screenshot", None)
        screenshot_frames = getattr(self.options, "screenshot_frames", 60)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.unicode:
                        key = ord(event.unicode)
                        if event.key == pygame.K_LEFT:
                            key = 0x08
                        if event.key == pygame.K_RIGHT:
                            key = 0x15
                        if key:
                            self.main.keyboard.pressed(chr(key))
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    touch = scene.Touch(1, scene._mouse_to_scene(event.pos))
                    self.main.keyboard.touch_began(touch)
                elif event.type == pygame.MOUSEBUTTONUP:
                    touch = scene.Touch(1, scene._mouse_to_scene(event.pos))
                    self.main.keyboard.touch_ended(touch)
                elif event.type == pygame.MOUSEMOTION:
                    if pygame.mouse.get_pressed()[0]:
                        touch = scene.Touch(1, scene._mouse_to_scene(event.pos))
                        self.main.keyboard.touch_moved(touch)

            self.runtime.run(self._steps_per_frame)

            # Update heatmap every 10 frames (~3 Hz)
            self._frame_count += 1
            if self._frame_count % 10 == 0:
                self._update_heatmap()

            surface = pygame.display.get_surface()

            # Draw keyboard + monitor panel (via _extra_drawables)
            self.main.keyboard.draw()
            # Draw heatmap (via HeatmapView)
            self._heatmap_view.draw()
            # Draw display on top — covers any keyboard bleed
            self.main.display.draw()

            pygame.display.flip()

            # Auto-screenshot mode: save after N frames and exit
            if screenshot_path and self._frame_count >= screenshot_frames:
                pygame.image.save(surface, screenshot_path)
                print(f"Screenshot saved to {screenshot_path}")
                return

            clock.tick(30)


if __name__ == "__main__":
    looper = Looper()
    looper.start()
