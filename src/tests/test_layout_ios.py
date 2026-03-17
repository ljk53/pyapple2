import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layout_ios import compute_layout, SAFE_AREA_TOP


class LayoutTests(unittest.TestCase):
    """Verify iOS layout calculations for iPhone XS Max (414x896)."""

    def setUp(self):
        self.layout = compute_layout(414, 896)

    def test_display_starts_at_or_below_safe_area(self):
        _, y, _, _ = self.layout["display"]
        self.assertGreaterEqual(y, SAFE_AREA_TOP)

    def test_display_fills_width(self):
        x, _, w, _ = self.layout["display"]
        self.assertEqual(x, 0)
        self.assertEqual(w, 414)

    def test_display_preserves_aspect_ratio(self):
        _, _, w, h = self.layout["display"]
        expected_h = round(384 * 414 / 560)
        self.assertEqual(h, expected_h)

    def test_registers_below_display(self):
        _, dy, _, dh = self.layout["display"]
        _, ry, _, _ = self.layout["registers"]
        self.assertGreater(ry, dy + dh - 1)

    def test_heatmap_below_registers(self):
        _, ry, _, rh = self.layout["registers"]
        _, hy, _, _ = self.layout["heatmap"]
        self.assertGreater(hy, ry + rh - 1)

    def test_heatmap_above_keyboard(self):
        _, hy, _, hsz = self.layout["heatmap"]
        kbd_top = self.layout["keyboard_top"]
        self.assertLess(hy + hsz, kbd_top)

    def test_heatmap_centered_horizontally(self):
        hx, _, hsz, _ = self.layout["heatmap"]
        center = hx + hsz / 2
        self.assertAlmostEqual(center, 414 / 2, delta=1)

    def test_heatmap_size_at_most_256(self):
        _, _, hsz, _ = self.layout["heatmap"]
        self.assertLessEqual(hsz, 256)

    def test_no_overlap(self):
        """All regions must be non-overlapping top-to-bottom."""
        _, dy, _, dh = self.layout["display"]
        _, ry, _, rh = self.layout["registers"]
        _, hy, _, hh = self.layout["heatmap"]
        kbd_top = self.layout["keyboard_top"]

        self.assertLessEqual(dy + dh, ry)
        self.assertLessEqual(ry + rh, hy)
        self.assertLessEqual(hy + hh, kbd_top)


if __name__ == "__main__":
    unittest.main()
