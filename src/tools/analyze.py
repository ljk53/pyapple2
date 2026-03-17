"""
Apple II Analysis Toolkit - Integrated Driver.

Combines tracing, stack analysis, and formatters into a single
unified analysis pipeline. Can run live analysis or analyze
existing trace files.

Usage:
    # Analyze boot sequence
    python -m tools.analyze --boot --cycles 10000

    # Generate LLM prompt
    python -m tools.analyze --cycles 5000 --format llm > prompt.md

    # Analyze existing trace
    python -m tools.analyze trace.jsonl --format tree

    # Full analysis to directory
    python -m tools.analyze --boot --output-dir ./analysis/
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from typing import Any

from tools.trace_logger import TraceLogger, TraceRecord, CPUTracer
from tools.stack_analyzer import StackAnalyzer, AnalysisResult
from tools.symbol_table import SymbolTable
from tools.formatters import TextFormatter, MarkdownFormatter, LLMPromptFormatter, JSONLFormatter


@dataclass
class AnalysisBundle:
    """
    Bundle of all analysis results.

    Provides unified access to trace, call analysis, and symbols,
    with multiple output format options.
    """

    trace_records: list[TraceRecord]
    call_result: AnalysisResult | None
    symbols: SymbolTable | None
    boot_analysis: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_text(self, limit: int = 100) -> str:
        """Format as plain text."""
        lines = []
        lines.append("=" * 60)
        lines.append("Apple II Analysis Results")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Trace records: {len(self.trace_records)}")

        if self.call_result:
            lines.append(f"Total calls: {self.call_result.total_calls}")
            lines.append(f"Max depth: {self.call_result.max_depth}")
            if self.call_result.anomalies:
                lines.append(f"Anomalies: {len(self.call_result.anomalies)}")

        lines.append("")
        lines.append("--- Trace ---")
        lines.append(TextFormatter.format_trace(self.trace_records, self.symbols, limit))

        if self.call_result and self.call_result.calls:
            lines.append("")
            lines.append("--- Call Tree ---")
            lines.append(self.call_result.format_tree())

        return "\n".join(lines)

    def to_json(self) -> str:
        """Format as JSON."""
        d = {
            "trace_count": len(self.trace_records),
            "metadata": self.metadata,
        }

        if self.call_result:
            d["call_analysis"] = self.call_result.to_dict()

        return json.dumps(d, indent=2)

    def to_llm_prompt(self, context: str = "") -> str:
        """Format as LLM-ready analysis prompt."""
        if self.boot_analysis:
            return LLMPromptFormatter.format_boot_sequence_analysis(self.trace_records, self.call_result, self.symbols)
        else:
            return LLMPromptFormatter.format_trace_analysis(self.trace_records, self.call_result, self.symbols, context)

    def to_markdown(self, limit: int = 100) -> str:
        """Format as Markdown."""
        lines = []
        lines.append("# Apple II Analysis Results")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Trace records**: {len(self.trace_records)}")

        if self.call_result:
            lines.append(f"- **Total calls**: {self.call_result.total_calls}")
            lines.append(f"- **Max depth**: {self.call_result.max_depth}")
            if self.call_result.anomalies:
                lines.append(f"- **Anomalies**: {len(self.call_result.anomalies)}")
            if self.call_result.unclosed_calls:
                lines.append(f"- **Unclosed calls**: {len(self.call_result.unclosed_calls)}")

        lines.append("")
        lines.append("## Execution Trace")
        lines.append("")
        lines.append(MarkdownFormatter.format_trace(self.trace_records, self.symbols, limit))

        if self.call_result and self.call_result.calls:
            lines.append("")
            lines.append("## Call Hierarchy")
            lines.append("")
            lines.append(MarkdownFormatter.format_call_tree(self.call_result))

            # Add profile
            profile = self.call_result.profile_by_target()
            if profile:
                lines.append("")
                lines.append("## Profile by Target")
                lines.append("")
                lines.append(MarkdownFormatter.format_profile(profile, self.symbols))

        return "\n".join(lines)

    def to_jsonl(self) -> str:
        """Format trace as JSONL."""
        return JSONLFormatter.format_records(self.trace_records)

    def get_profile(self) -> dict[int, dict[str, Any]]:
        """Get call profile by target address."""
        if self.call_result:
            return self.call_result.profile_by_target()
        return {}

    def save_to_directory(self, output_dir: str) -> None:
        """Save all analysis outputs to a directory."""
        os.makedirs(output_dir, exist_ok=True)

        # Save trace as JSONL
        trace_path = os.path.join(output_dir, "trace.jsonl")
        with open(trace_path, "w") as f:
            f.write(self.to_jsonl())

        # Save call analysis as JSON
        if self.call_result:
            calls_path = os.path.join(output_dir, "calls.json")
            with open(calls_path, "w") as f:
                f.write(self.call_result.to_json())

        # Save analysis as markdown
        md_path = os.path.join(output_dir, "analysis.md")
        with open(md_path, "w") as f:
            f.write(self.to_markdown())

        # Save LLM prompt
        llm_path = os.path.join(output_dir, "llm_prompt.md")
        with open(llm_path, "w") as f:
            f.write(self.to_llm_prompt())

    def save_llm_prompt(self, path: str) -> None:
        """Save LLM prompt to file."""
        with open(path, "w") as f:
            f.write(self.to_llm_prompt())


class Analyzer:
    """
    Integrated Apple II analysis driver.

    Combines CPU tracing, stack analysis, and symbol resolution
    into a unified analysis pipeline.
    """

    def __init__(
        self,
        max_cycles: int = 10000,
        use_symbols: bool = True,
        trace_file: str | None = None,
        address_range: tuple[int, int] | None = None,
        calls_only: bool = False,
        boot_analysis: bool = False,
    ) -> None:
        """
        Create an analyzer.

        Args:
            max_cycles: Maximum cycles to execute (if not using trace_file)
            use_symbols: Whether to load built-in symbol table
            trace_file: Path to existing trace file to analyze
            address_range: (start, end) tuple to filter addresses
            calls_only: Only include JSR/RTS/RTI instructions
            boot_analysis: Use boot sequence specific analysis
        """
        self.max_cycles = max_cycles
        self.use_symbols = use_symbols
        self.trace_file = trace_file
        self.address_range = address_range
        self.calls_only = calls_only
        self.boot_analysis = boot_analysis

        self.symbols = SymbolTable.with_builtins() if use_symbols else None

    def run(self) -> AnalysisBundle:
        """
        Run the analysis.

        Returns an AnalysisBundle with all results.
        """
        if self.trace_file:
            return self._analyze_trace_file()
        else:
            return self._run_live_analysis()

    def _run_live_analysis(self) -> AnalysisBundle:
        """Run live CPU tracing and analysis."""
        import argparse as _argparse
        from runtime import Runtime

        rom_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "bin", "A2SOFT2.BIN")
        opts = _argparse.Namespace(
            rom=rom_path if os.path.exists(rom_path) else None,
            ram=None,
            disk=None, disk2=None,
            throttle=False, controller=None,
        )
        runtime = Runtime(opts)
        cpu = runtime.cpu

        # Set up tracer
        tracer = CPUTracer(cpu, runtime.bus, self.symbols)
        tracer.start()

        # Run
        for _ in range(self.max_cycles):
            cpu.step()

        tracer.stop()
        records = tracer.get_records()

        # Apply filters
        records = self._apply_filters(records)

        # Analyze
        analyzer = StackAnalyzer(symbols=self.symbols)
        call_result = analyzer.analyze(records)

        return AnalysisBundle(
            trace_records=records,
            call_result=call_result,
            symbols=self.symbols,
            boot_analysis=self.boot_analysis,
            metadata={
                "cycles": self.max_cycles,
                "source": "live",
            },
        )

    def _analyze_trace_file(self) -> AnalysisBundle:
        """Analyze an existing trace file."""
        assert self.trace_file is not None
        logger = TraceLogger.load(self.trace_file)
        records = logger.get_records()

        # Apply filters
        records = self._apply_filters(records)

        # Analyze
        analyzer = StackAnalyzer(symbols=self.symbols)
        call_result = analyzer.analyze(records)

        return AnalysisBundle(
            trace_records=records,
            call_result=call_result,
            symbols=self.symbols,
            boot_analysis=self.boot_analysis,
            metadata={
                "source": self.trace_file,
            },
        )

    def _apply_filters(self, records: list[TraceRecord]) -> list[TraceRecord]:
        """Apply configured filters to records."""
        result = records

        if self.address_range:
            start, end = self.address_range
            result = [r for r in result if start <= r.pc <= end]

        if self.calls_only:
            result = [r for r in result if r.mnemonic in ("JSR", "RTS", "RTI")]

        return result


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Apple II Analysis Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze boot sequence, output LLM prompt
  python -m tools.analyze --boot --cycles 10000 --format llm

  # Quick trace with call tree
  python -m tools.analyze --cycles 5000 --format tree

  # Analyze existing trace file
  python -m tools.analyze trace.jsonl --format markdown

  # Save all outputs to directory
  python -m tools.analyze --boot --output-dir ./analysis/
""",
    )

    parser.add_argument("trace_file", nargs="?", help="Existing trace file to analyze (JSONL format)")

    parser.add_argument("-n", "--cycles", type=int, default=10000, help="Maximum cycles to execute (default: 10000)")

    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json", "jsonl", "markdown", "tree", "llm", "profile"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument("-o", "--output", metavar="FILE", help="Output file (default: stdout)")

    parser.add_argument("--output-dir", metavar="DIR", help="Save all outputs to directory")

    parser.add_argument("--boot", action="store_true", help="Use boot sequence analysis mode")

    parser.add_argument("--no-symbols", action="store_true", help="Don't load symbol table")

    parser.add_argument("--range", metavar="START-END", help="Filter by address range (e.g., D000-FFFF)")

    parser.add_argument("--calls-only", action="store_true", help="Only include JSR/RTS/RTI instructions")

    parser.add_argument("--limit", type=int, default=100, help="Limit trace output lines (default: 100)")

    return parser.parse_args(args)


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Parse address range if provided
    address_range = None
    if args.range:
        parts = args.range.split("-")
        if len(parts) == 2:
            address_range = (int(parts[0], 16), int(parts[1], 16))

    # Create analyzer
    analyzer = Analyzer(
        max_cycles=args.cycles,
        use_symbols=not args.no_symbols,
        trace_file=args.trace_file,
        address_range=address_range,
        calls_only=args.calls_only,
        boot_analysis=args.boot,
    )

    # Run analysis
    result = analyzer.run()

    # Handle output directory
    if args.output_dir:
        result.save_to_directory(args.output_dir)
        print(f"Saved analysis to {args.output_dir}/")
        return

    # Generate output
    if args.format == "text":
        output = result.to_text(args.limit)
    elif args.format == "json":
        output = result.to_json()
    elif args.format == "jsonl":
        output = result.to_jsonl()
    elif args.format == "markdown":
        output = result.to_markdown(args.limit)
    elif args.format == "tree":
        if result.call_result:
            output = result.call_result.format_tree()
            output += f"\n\nMax depth: {result.call_result.max_depth}"
            output += f"\nTotal calls: {result.call_result.total_calls}"
        else:
            output = "No call data available"
    elif args.format == "llm":
        output = result.to_llm_prompt()
    elif args.format == "profile":
        profile = result.get_profile()
        lines = ["Target          Calls   Cycles   Avg"]
        lines.append("-" * 45)
        for target, data in sorted(profile.items(), key=lambda x: -x[1]["total_cycles"]):
            name = f"${target:04X}"
            if result.symbols:
                sym = result.symbols.lookup(target)
                if sym:
                    name = f"{sym.name:12s}"
            avg = data["total_cycles"] // data["call_count"] if data["call_count"] else 0
            lines.append(f"{name:<16} {data['call_count']:>5} {data['total_cycles']:>8} {avg:>6}")
        output = "\n".join(lines)

    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Wrote output to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
