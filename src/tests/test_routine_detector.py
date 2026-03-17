"""
Tests for routine detector.

TDD: Tests written first, before implementation.
"""

import unittest

from tools.trace_logger import TraceRecord


def _rec(seq, pc, opcode, mnemonic, operand=""):
    """Helper to create TraceRecord with defaults."""
    return TraceRecord(
        seq=seq,
        cycle=seq * 2,
        pc=pc,
        opcode=opcode,
        mnemonic=mnemonic,
        operand=operand,
        a=0,
        x=0,
        y=0,
        sp=0xFF,
        p=0x34,
    )


class TestFindEntryPoints(unittest.TestCase):
    """Tests for finding JSR targets as entry points."""

    def test_find_single_jsr_target(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x0300, 0x20, "JSR", "$FDED"),
            _rec(2, 0xFDED, 0xA9, "LDA", "#$41"),
            _rec(3, 0xFDEF, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        entries = detector.find_entry_points(records)
        self.assertIn(0xFDED, entries)

    def test_find_multiple_entry_points(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x6100, 0x20, "JSR", "$6C82"),
            _rec(2, 0x6C82, 0x20, "JSR", "$6CDB"),
            _rec(3, 0x6CDB, 0xA9, "LDA", "#$00"),
            _rec(4, 0x6CDD, 0x60, "RTS"),
            _rec(5, 0x6C85, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        entries = detector.find_entry_points(records)
        self.assertIn(0x6C82, entries)
        self.assertIn(0x6CDB, entries)

    def test_no_entry_points_without_jsr(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x0300, 0xA9, "LDA", "#$00"),
            _rec(2, 0x0302, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        entries = detector.find_entry_points(records)
        self.assertEqual(len(entries), 0)


class TestBuildBasicBlocks(unittest.TestCase):
    """Tests for basic block construction."""

    def test_straight_line_is_one_block(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x0300, 0xA9, "LDA", "#$00"),
            _rec(2, 0x0302, 0x85, "STA", "$42"),
            _rec(3, 0x0304, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        blocks = detector.build_basic_blocks(records)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].start_addr, 0x0300)

    def test_branch_creates_multiple_blocks(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x0300, 0xA9, "LDA", "#$00"),
            _rec(2, 0x0302, 0xD0, "BNE", "$0306"),
            # Fall-through path
            _rec(3, 0x0304, 0xEA, "NOP"),
            # Branch target
            _rec(4, 0x0306, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        blocks = detector.build_basic_blocks(records)
        self.assertGreaterEqual(len(blocks), 2)

    def test_jmp_ends_block(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x0300, 0xA9, "LDA", "#$00"),
            _rec(2, 0x0302, 0x4C, "JMP", "$0400"),
            _rec(3, 0x0400, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        blocks = detector.build_basic_blocks(records)
        self.assertGreaterEqual(len(blocks), 2)

    def test_block_has_successors(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x0300, 0xD0, "BNE", "$0304"),
            _rec(2, 0x0302, 0xEA, "NOP"),
            _rec(3, 0x0304, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        blocks = detector.build_basic_blocks(records)
        # First block should have successor(s)
        first = [b for b in blocks if b.start_addr == 0x0300][0]
        self.assertGreater(len(first.successors), 0)


class TestDetectLoops(unittest.TestCase):
    """Tests for loop detection via back-edges."""

    def test_detect_simple_loop(self):
        from tools.routine_detector import RoutineDetector

        # LDX #5; loop: DEX; BNE loop
        records = [
            _rec(1, 0x0300, 0xA2, "LDX", "#$05"),
            _rec(2, 0x0302, 0xCA, "DEX"),
            _rec(3, 0x0303, 0xD0, "BNE", "$0302"),
            _rec(4, 0x0302, 0xCA, "DEX"),
            _rec(5, 0x0303, 0xD0, "BNE", "$0302"),
        ]
        detector = RoutineDetector()
        blocks = detector.build_basic_blocks(records)
        loops = detector.detect_loops(blocks)
        self.assertGreater(len(loops), 0)

    def test_no_loop_in_straight_code(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x0300, 0xA9, "LDA", "#$00"),
            _rec(2, 0x0302, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        blocks = detector.build_basic_blocks(records)
        loops = detector.detect_loops(blocks)
        self.assertEqual(len(loops), 0)


class TestDetectFromTrace(unittest.TestCase):
    """Tests for full routine detection from trace."""

    def test_detect_single_routine(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x0300, 0x20, "JSR", "$0400"),
            _rec(2, 0x0400, 0xA9, "LDA", "#$42"),
            _rec(3, 0x0402, 0x60, "RTS"),
            _rec(4, 0x0303, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        routines = detector.detect_from_trace(records)
        self.assertGreater(len(routines), 0)
        addrs = {r.entry_addr for r in routines}
        self.assertIn(0x0400, addrs)

    def test_routine_has_call_targets(self):
        from tools.routine_detector import RoutineDetector

        records = [
            _rec(1, 0x0300, 0x20, "JSR", "$0400"),
            _rec(2, 0x0400, 0x20, "JSR", "$0500"),
            _rec(3, 0x0500, 0x60, "RTS"),
            _rec(4, 0x0403, 0x60, "RTS"),
            _rec(5, 0x0303, 0x60, "RTS"),
        ]
        detector = RoutineDetector()
        routines = detector.detect_from_trace(records)
        routine_0400 = [r for r in routines if r.entry_addr == 0x0400]
        self.assertEqual(len(routine_0400), 1)
        self.assertIn(0x0500, routine_0400[0].calls)

    def test_detect_with_symbols(self):
        from tools.routine_detector import RoutineDetector
        from tools.symbol_table import SymbolTable

        symbols = SymbolTable()
        symbols.add(0x0400, "my_routine", "routine", "test")
        records = [
            _rec(1, 0x0300, 0x20, "JSR", "$0400"),
            _rec(2, 0x0400, 0xA9, "LDA", "#$42"),
            _rec(3, 0x0402, 0x60, "RTS"),
            _rec(4, 0x0303, 0x60, "RTS"),
        ]
        detector = RoutineDetector(symbols=symbols)
        routines = detector.detect_from_trace(records)
        routine_0400 = [r for r in routines if r.entry_addr == 0x0400]
        self.assertEqual(routine_0400[0].name, "my_routine")


class TestRoutineDataclass(unittest.TestCase):
    """Tests for the Routine dataclass."""

    def test_routine_fields(self):
        from tools.routine_detector import Routine

        r = Routine(
            entry_addr=0x0400,
            name="test",
            blocks=[],
            calls=set(),
            callers=set(),
            loops=[],
            instruction_count=10,
            cycle_count=20,
        )
        self.assertEqual(r.entry_addr, 0x0400)
        self.assertEqual(r.name, "test")

    def test_basic_block_fields(self):
        from tools.routine_detector import BasicBlock

        b = BasicBlock(
            start_addr=0x0300,
            end_addr=0x0304,
            instructions=[],
            successors=[0x0306],
            predecessors=[],
        )
        self.assertEqual(b.start_addr, 0x0300)
        self.assertEqual(b.successors, [0x0306])


if __name__ == "__main__":
    unittest.main()
