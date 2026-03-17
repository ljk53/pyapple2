"""
Tests for shared headless module.

TDD: Tests written first, before implementation.
"""

import unittest

from memory import ObservableMemory


class TestHeadlessDisplay(unittest.TestCase):
    """Tests for HeadlessDisplay."""

    def _make_display(self):
        from headless import HeadlessDisplay

        mem = ObservableMemory()
        display = HeadlessDisplay(mem)
        return mem, display

    def test_create_display(self):
        """Display can be created with ObservableMemory."""
        from headless import HeadlessDisplay

        mem = ObservableMemory()
        display = HeadlessDisplay(mem)
        self.assertIsNotNone(display)

    def test_initial_screen_blank(self):
        """Screen is blank initially."""
        _, display = self._make_display()
        screen = display.get_screen()
        self.assertEqual(len(screen.split("\n")), 24)
        self.assertTrue(all(c == " " or c == "\n" for c in screen))

    def test_write_to_screen_memory(self):
        """Writing to $0400 range updates screen."""
        mem, display = self._make_display()
        # 'A' in Apple II encoding = 0xC1
        mem[0x400] = 0xC1
        screen = display.get_screen()
        self.assertIn("A", screen)

    def test_screen_address_mapping(self):
        """Apple II screen memory mapping is correct for row 0, col 0."""
        mem, display = self._make_display()
        mem[0x400] = 0xC1  # 'A'
        # Row 0, col 0
        self.assertEqual(display.screen[0][0], "A")

    def test_has_prompt_false_initially(self):
        """No prompt on blank screen."""
        _, display = self._make_display()
        self.assertFalse(display.has_prompt())

    def test_has_prompt_detects_bracket(self):
        """Detects ']' prompt on screen."""
        mem, display = self._make_display()
        # ']' in Apple II encoding = 0xDD
        mem[0x400] = 0xDD
        self.assertTrue(display.has_prompt())

    def test_count_prompts(self):
        """Counts lines with prompts."""
        mem, display = self._make_display()
        self.assertEqual(display.count_prompts(), 0)
        # Write ']' to row 0 ($0400) and row 1 ($0480)
        mem[0x400] = 0xDD
        mem[0x480] = 0xDD
        self.assertEqual(display.count_prompts(), 2)


class TestHeadlessKeyboard(unittest.TestCase):
    """Tests for HeadlessKeyboard."""

    def _make_keyboard(self):
        from headless import HeadlessKeyboard

        mem = ObservableMemory()
        kb = HeadlessKeyboard(mem)
        return mem, kb

    def test_create_keyboard(self):
        """Keyboard can be created with ObservableMemory."""
        from headless import HeadlessKeyboard

        mem = ObservableMemory()
        kb = HeadlessKeyboard(mem)
        self.assertIsNotNone(kb)

    def test_no_key_initially(self):
        """No key available initially (bit 7 clear)."""
        mem, kb = self._make_keyboard()
        self.assertEqual(mem[0xC000] & 0x80, 0)

    def test_type_key_char(self):
        """Can type a character key."""
        mem, kb = self._make_keyboard()
        kb.type_key("A")
        self.assertEqual(mem[0xC000], 0x80 | ord("A"))

    def test_type_key_int(self):
        """Can type a key by integer value."""
        mem, kb = self._make_keyboard()
        kb.type_key(0x0D)  # Enter
        self.assertEqual(mem[0xC000], 0x80 | 0x0D)

    def test_type_string(self):
        """Can type a string (with CR appended)."""
        mem, kb = self._make_keyboard()
        kb.type_string("AB")
        # First char available immediately
        self.assertEqual(mem[0xC000], 0x80 | ord("A"))
        # Read $C010 to clear and advance
        mem[0xC010]
        self.assertEqual(mem[0xC000], 0x80 | ord("B"))
        mem[0xC010]
        self.assertEqual(mem[0xC000], 0x80 | 0x0D)  # CR appended

    def test_keyboard_buffer(self):
        """Keys buffer when previous key not consumed."""
        mem, kb = self._make_keyboard()
        kb.type_key("A")
        kb.type_key("B")
        # 'A' available first
        self.assertEqual(mem[0xC000], 0x80 | ord("A"))
        # Clear strobe -> 'B' becomes available
        mem[0xC010]
        self.assertEqual(mem[0xC000], 0x80 | ord("B"))

    def test_clear_strobe(self):
        """Reading $C010 clears current key and advances buffer."""
        mem, kb = self._make_keyboard()
        kb.type_key("X")
        self.assertEqual(mem[0xC000], 0x80 | ord("X"))
        mem[0xC010]  # clear
        # No more keys, bit 7 should be clear
        self.assertEqual(mem[0xC000] & 0x80, 0)


class TestBootToPrompt(unittest.TestCase):
    """Tests for boot_to_prompt utility."""

    def test_boot_to_prompt_returns_steps(self):
        """boot_to_prompt returns number of steps (instructions) run."""
        from headless import boot_to_prompt, HeadlessDisplay
        import cpu_mpu6502

        mem = ObservableMemory()
        # Load a minimal ROM that just loops: JMP $D000
        mem[0xD000] = 0x4C  # JMP
        mem[0xD001] = 0x00
        mem[0xD002] = 0xD0
        # Set reset vector
        mem[0xFFFC] = 0x00
        mem[0xFFFD] = 0xD0

        cpu = cpu_mpu6502.MPU(mem)
        display = HeadlessDisplay(mem)
        cpu.reset()

        # Should run max_steps and return (no prompt will appear)
        result = boot_to_prompt(cpu, display, max_steps=1000)
        self.assertEqual(result, 1000)

    def test_boot_to_prompt_stops_at_prompt(self):
        """boot_to_prompt stops when prompt detected."""
        from headless import boot_to_prompt, HeadlessDisplay
        import cpu_mpu6502

        mem = ObservableMemory()

        # ROM: just loop
        mem[0xD000] = 0x4C
        mem[0xD001] = 0x00
        mem[0xD002] = 0xD0
        mem[0xFFFC] = 0x00
        mem[0xFFFD] = 0xD0

        cpu = cpu_mpu6502.MPU(mem)
        display = HeadlessDisplay(mem)
        cpu.reset()

        # Write ']' to screen AFTER display is subscribed
        mem[0x400] = 0xDD

        steps = boot_to_prompt(cpu, display, max_steps=1000000)
        # Should stop early (at first 10000-step check)
        self.assertLessEqual(steps, 10001)


if __name__ == "__main__":
    unittest.main()
