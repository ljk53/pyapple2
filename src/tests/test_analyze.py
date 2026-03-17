"""
Tests for analyze module - the integrated analysis driver.

TDD: These tests are written first, before the implementation.
"""

import unittest
import tempfile
import os
import json


class TestAnalyzerConfig(unittest.TestCase):
    """Tests for analyzer configuration."""

    def test_create_default_config(self):
        """Can create analyzer with default config."""
        from tools.analyze import Analyzer

        analyzer = Analyzer()
        self.assertIsNotNone(analyzer)

    def test_config_with_cycles(self):
        """Can configure max cycles."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(max_cycles=5000)
        self.assertEqual(analyzer.max_cycles, 5000)

    def test_config_with_symbols(self):
        """Can configure to use symbols."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(use_symbols=True)
        self.assertTrue(analyzer.use_symbols)


class TestAnalyzerExecution(unittest.TestCase):
    """Tests for analyzer execution."""

    def test_run_returns_result(self):
        """Running analyzer returns an AnalysisBundle."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(max_cycles=100)
        result = analyzer.run()
        self.assertIsNotNone(result)

    def test_result_has_trace(self):
        """Result contains trace records."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(max_cycles=100)
        result = analyzer.run()
        self.assertTrue(hasattr(result, "trace_records"))
        self.assertGreater(len(result.trace_records), 0)

    def test_result_has_call_analysis(self):
        """Result contains call analysis."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(max_cycles=1000)
        result = analyzer.run()
        self.assertTrue(hasattr(result, "call_result"))

    def test_result_has_symbols(self):
        """Result contains symbol table."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(max_cycles=100, use_symbols=True)
        result = analyzer.run()
        self.assertTrue(hasattr(result, "symbols"))
        self.assertIsNotNone(result.symbols)


class TestAnalysisBundleOutput(unittest.TestCase):
    """Tests for AnalysisBundle output methods."""

    def setUp(self):
        """Set up with a small analysis run."""
        from tools.analyze import Analyzer

        self.analyzer = Analyzer(max_cycles=500, use_symbols=True)
        self.result = self.analyzer.run()

    def test_to_text(self):
        """Can output as text."""
        text = self.result.to_text()
        self.assertIn("trace", text.lower())

    def test_to_json(self):
        """Can output as JSON."""
        json_str = self.result.to_json()
        d = json.loads(json_str)
        self.assertIn("trace_count", d)

    def test_to_llm_prompt(self):
        """Can output as LLM prompt."""
        prompt = self.result.to_llm_prompt()
        self.assertIn("Apple II", prompt)
        self.assertIn("Analysis", prompt)

    def test_to_markdown(self):
        """Can output as markdown."""
        md = self.result.to_markdown()
        self.assertIn("#", md)  # Has headers


class TestAnalyzerSaveOutput(unittest.TestCase):
    """Tests for saving analysis output."""

    def test_save_to_directory(self):
        """Can save all outputs to a directory."""
        from tools.analyze import Analyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = Analyzer(max_cycles=500, use_symbols=True)
            result = analyzer.run()
            result.save_to_directory(tmpdir)

            # Check files were created
            files = os.listdir(tmpdir)
            self.assertIn("trace.jsonl", files)
            self.assertIn("calls.json", files)
            self.assertIn("analysis.md", files)

    def test_save_llm_prompt(self):
        """Can save LLM prompt to file."""
        from tools.analyze import Analyzer

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = f.name

        try:
            analyzer = Analyzer(max_cycles=500)
            result = analyzer.run()
            result.save_llm_prompt(temp_path)

            with open(temp_path) as f:
                content = f.read()

            self.assertIn("Apple II", content)
        finally:
            os.unlink(temp_path)


class TestAnalyzerWithTraceFile(unittest.TestCase):
    """Tests for analyzing existing trace files."""

    def test_load_trace_file(self):
        """Can analyze from existing trace file."""
        from tools.analyze import Analyzer
        from tools.trace_logger import TraceRecord

        # Create a test trace file
        records = [
            {
                "seq": 1,
                "cycle": 100,
                "pc": "0300",
                "op": "20",
                "mnemonic": "JSR",
                "operand": "$FDED",
                "a": "00",
                "x": "00",
                "y": "00",
                "sp": "FF",
                "p": "34",
            },
            {
                "seq": 2,
                "cycle": 110,
                "pc": "FDED",
                "op": "60",
                "mnemonic": "RTS",
                "operand": "",
                "a": "00",
                "x": "00",
                "y": "00",
                "sp": "FD",
                "p": "34",
            },
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
            temp_path = f.name

        try:
            analyzer = Analyzer(trace_file=temp_path)
            result = analyzer.run()
            self.assertEqual(len(result.trace_records), 2)
        finally:
            os.unlink(temp_path)


class TestAnalyzerFilters(unittest.TestCase):
    """Tests for trace filtering during analysis."""

    def test_filter_by_address_range(self):
        """Can filter trace by address range."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(max_cycles=1000, address_range=(0xF000, 0xFFFF))
        result = analyzer.run()
        # All records should be in ROM range
        for record in result.trace_records:
            self.assertGreaterEqual(record.pc, 0xF000)

    def test_filter_calls_only(self):
        """Can filter to only JSR/RTS instructions."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(max_cycles=1000, calls_only=True)
        result = analyzer.run()
        # All records should be call-related
        for record in result.trace_records:
            self.assertIn(record.mnemonic, ["JSR", "RTS", "RTI"])


class TestCLIInterface(unittest.TestCase):
    """Tests for command line interface."""

    def test_parse_cycles_arg(self):
        """Can parse --cycles argument."""
        from tools.analyze import parse_args

        args = parse_args(["--cycles", "5000"])
        self.assertEqual(args.cycles, 5000)

    def test_parse_output_arg(self):
        """Can parse --output argument."""
        from tools.analyze import parse_args

        args = parse_args(["--output", "result.md"])
        self.assertEqual(args.output, "result.md")

    def test_parse_format_arg(self):
        """Can parse --format argument."""
        from tools.analyze import parse_args

        args = parse_args(["--format", "llm"])
        self.assertEqual(args.format, "llm")

    def test_parse_boot_flag(self):
        """Can parse --boot flag."""
        from tools.analyze import parse_args

        args = parse_args(["--boot"])
        self.assertTrue(args.boot)

    def test_parse_trace_file_arg(self):
        """Can parse trace file argument."""
        from tools.analyze import parse_args

        args = parse_args(["trace.jsonl"])
        self.assertEqual(args.trace_file, "trace.jsonl")


class TestBootSequenceAnalysis(unittest.TestCase):
    """Tests for boot sequence specific analysis."""

    def test_boot_analysis(self):
        """Boot analysis includes boot-specific context."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(max_cycles=5000, boot_analysis=True)
        result = analyzer.run()
        prompt = result.to_llm_prompt()
        self.assertIn("boot", prompt.lower())


class TestProfileOutput(unittest.TestCase):
    """Tests for profiling output."""

    def test_profile_by_routine(self):
        """Can generate profile by routine."""
        from tools.analyze import Analyzer

        analyzer = Analyzer(max_cycles=5000, use_symbols=True)
        result = analyzer.run()
        profile = result.get_profile()
        self.assertIsNotNone(profile)
        # Profile should have entries
        self.assertGreater(len(profile), 0)


if __name__ == "__main__":
    unittest.main()
