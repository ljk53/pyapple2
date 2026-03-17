"""
Tests for stack_analyzer module.

TDD: These tests are written first, before the implementation.
"""

import unittest
import json


class TestCallFrame(unittest.TestCase):
    """Tests for CallFrame dataclass."""

    def test_create_call_frame(self):
        """Can create a call frame."""
        from tools.stack_analyzer import CallFrame

        frame = CallFrame(
            caller_pc=0x0300,
            target_pc=0xFDED,
            return_addr=0x0303,
            entry_sp=0xFD,
            entry_cycle=100,
            entry_seq=5,
        )
        self.assertEqual(frame.caller_pc, 0x0300)
        self.assertEqual(frame.target_pc, 0xFDED)
        self.assertEqual(frame.return_addr, 0x0303)


class TestCallRecord(unittest.TestCase):
    """Tests for CallRecord dataclass."""

    def test_create_call_record(self):
        """Can create a call record."""
        from tools.stack_analyzer import CallFrame, CallRecord

        frame = CallFrame(0x0300, 0xFDED, 0x0303, 0xFD, 100, 5)
        record = CallRecord(frame=frame, exit_cycle=200, exit_seq=15)
        self.assertEqual(record.frame.target_pc, 0xFDED)
        self.assertEqual(record.exit_cycle, 200)

    def test_call_record_duration(self):
        """CallRecord calculates duration in cycles."""
        from tools.stack_analyzer import CallFrame, CallRecord

        frame = CallFrame(0x0300, 0xFDED, 0x0303, 0xFD, 100, 5)
        record = CallRecord(frame=frame, exit_cycle=200, exit_seq=15)
        self.assertEqual(record.duration, 100)

    def test_call_record_with_children(self):
        """CallRecord can have nested child calls."""
        from tools.stack_analyzer import CallFrame, CallRecord

        parent_frame = CallFrame(0x0300, 0xFDED, 0x0303, 0xFD, 100, 5)
        child_frame = CallFrame(0xFDF0, 0xFC58, 0xFDF3, 0xFB, 110, 7)
        child = CallRecord(frame=child_frame, exit_cycle=150, exit_seq=12)

        parent = CallRecord(frame=parent_frame, exit_cycle=200, exit_seq=15)
        parent.children.append(child)

        self.assertEqual(len(parent.children), 1)
        self.assertEqual(parent.children[0].frame.target_pc, 0xFC58)

    def test_call_record_to_dict(self):
        """CallRecord can be converted to dict."""
        from tools.stack_analyzer import CallFrame, CallRecord

        frame = CallFrame(0x0300, 0xFDED, 0x0303, 0xFD, 100, 5)
        record = CallRecord(frame=frame, exit_cycle=200, exit_seq=15)
        d = record.to_dict()
        self.assertEqual(d["target"], "FDED")
        self.assertEqual(d["caller"], "0300")
        self.assertEqual(d["duration"], 100)


class TestStackAnalyzer(unittest.TestCase):
    """Tests for StackAnalyzer class."""

    def test_create_stack_analyzer(self):
        """Can create a stack analyzer."""
        from tools.stack_analyzer import StackAnalyzer

        analyzer = StackAnalyzer()
        self.assertIsNotNone(analyzer)

    def test_analyze_simple_jsr_rts(self):
        """Can analyze a simple JSR/RTS pair."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$FDED", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 102, 0xFDED, 0xA9, "LDA", "#$00", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(3, 104, 0xFDEF, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(4, 106, 0x0303, 0xEA, "NOP", "", 0, 0, 0, 0xFF, 0x34),
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)

        self.assertEqual(len(result.calls), 1)
        self.assertEqual(result.calls[0].frame.target_pc, 0xFDED)
        self.assertEqual(result.calls[0].frame.caller_pc, 0x0300)

    def test_analyze_nested_calls(self):
        """Can analyze nested JSR calls."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$1000", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 102, 0x1000, 0x20, "JSR", "$2000", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(3, 104, 0x2000, 0xEA, "NOP", "", 0, 0, 0, 0xFB, 0x34),
            TraceRecord(4, 106, 0x2001, 0x60, "RTS", "", 0, 0, 0, 0xFB, 0x34),
            TraceRecord(5, 108, 0x1003, 0xEA, "NOP", "", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(6, 110, 0x1004, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(7, 112, 0x0303, 0xEA, "NOP", "", 0, 0, 0, 0xFF, 0x34),
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)

        # Should have one top-level call with one nested call
        self.assertEqual(len(result.calls), 1)
        self.assertEqual(result.calls[0].frame.target_pc, 0x1000)
        self.assertEqual(len(result.calls[0].children), 1)
        self.assertEqual(result.calls[0].children[0].frame.target_pc, 0x2000)

    def test_track_max_depth(self):
        """Tracks maximum call depth."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$1000", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 102, 0x1000, 0x20, "JSR", "$2000", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(3, 104, 0x2000, 0x20, "JSR", "$3000", 0, 0, 0, 0xFB, 0x34),
            TraceRecord(4, 106, 0x3000, 0x60, "RTS", "", 0, 0, 0, 0xF9, 0x34),
            TraceRecord(5, 108, 0x2003, 0x60, "RTS", "", 0, 0, 0, 0xFB, 0x34),
            TraceRecord(6, 110, 0x1003, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(7, 112, 0x0303, 0x60, "RTS", "", 0, 0, 0, 0xFF, 0x34),
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)

        self.assertEqual(result.max_depth, 3)

    def test_count_total_calls(self):
        """Counts total number of calls."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$1000", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 102, 0x1000, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(3, 104, 0x0303, 0x20, "JSR", "$2000", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(4, 106, 0x2000, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(5, 108, 0x0306, 0xEA, "NOP", "", 0, 0, 0, 0xFF, 0x34),
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)

        self.assertEqual(result.total_calls, 2)

    def test_detect_unbalanced_stack(self):
        """Detects unbalanced stack (RTS without JSR)."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x60, "RTS", "", 0, 0, 0, 0xFF, 0x34),
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)

        self.assertTrue(len(result.anomalies) > 0)
        self.assertEqual(result.anomalies[0]["type"], "unmatched_rts")

    def test_detect_unclosed_calls(self):
        """Detects calls that were never returned from."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$1000", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 102, 0x1000, 0xEA, "NOP", "", 0, 0, 0, 0xFD, 0x34),
            # No RTS - trace ends
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)

        self.assertTrue(len(result.unclosed_calls) > 0)

    def test_generate_call_tree_text(self):
        """Can generate a text call tree."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$FDED", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 102, 0xFDED, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(3, 104, 0x0303, 0xEA, "NOP", "", 0, 0, 0, 0xFF, 0x34),
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)
        tree = result.format_tree()

        self.assertIn("FDED", tree)

    def test_with_symbol_table(self):
        """Uses symbol table for readable names."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord
        from tools.symbol_table import SymbolTable

        symbols = SymbolTable.with_builtins()

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$FDED", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 102, 0xFDED, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(3, 104, 0x0303, 0xEA, "NOP", "", 0, 0, 0, 0xFF, 0x34),
        ]

        analyzer = StackAnalyzer(symbols=symbols)
        result = analyzer.analyze(records)

        # Should include COUT in output
        tree = result.format_tree()
        self.assertIn("COUT", tree)


class TestAnalysisResult(unittest.TestCase):
    """Tests for AnalysisResult."""

    def test_result_to_dict(self):
        """Result can be converted to dict."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$FDED", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 102, 0xFDED, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)
        d = result.to_dict()

        self.assertIn("calls", d)
        self.assertIn("max_depth", d)
        self.assertIn("total_calls", d)

    def test_result_to_json(self):
        """Result can be serialized to JSON."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$FDED", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 102, 0xFDED, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)
        json_str = result.to_json()

        d = json.loads(json_str)
        self.assertIn("calls", d)


class TestCallProfile(unittest.TestCase):
    """Tests for call profiling."""

    def test_profile_by_target(self):
        """Can profile calls by target address."""
        from tools.stack_analyzer import StackAnalyzer
        from tools.trace_logger import TraceRecord

        records = [
            TraceRecord(1, 100, 0x0300, 0x20, "JSR", "$FDED", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(2, 110, 0xFDED, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
            TraceRecord(3, 112, 0x0303, 0x20, "JSR", "$FDED", 0, 0, 0, 0xFF, 0x34),
            TraceRecord(4, 122, 0xFDED, 0x60, "RTS", "", 0, 0, 0, 0xFD, 0x34),
        ]

        analyzer = StackAnalyzer()
        result = analyzer.analyze(records)
        profile = result.profile_by_target()

        self.assertIn(0xFDED, profile)
        self.assertEqual(profile[0xFDED]["call_count"], 2)
        self.assertEqual(profile[0xFDED]["total_cycles"], 20)


if __name__ == "__main__":
    unittest.main()
