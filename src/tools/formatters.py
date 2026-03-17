"""
Output Formatters for Apple II Analysis Toolkit.

Provides various output formats for traces and analysis results,
including LLM-friendly prompts for AI-assisted reverse engineering.
"""

from __future__ import annotations

import json
from typing import Any


class TextFormatter:
    """Plain text output formatter."""

    @staticmethod
    def format_trace(records: list[Any], symbols: Any = None, limit: int = 50) -> str:
        """Format trace records as text table."""
        lines = []
        lines.append(f"{'#':>6} {'Addr':>6} {'Instruction':<16} {'A':>4} {'X':>4} {'Y':>4} {'SP':>4} {'Flags':<8}")
        lines.append("-" * 60)

        for record in records[:limit]:
            flags = ""
            flags += "N" if record.p & 0x80 else "-"
            flags += "V" if record.p & 0x40 else "-"
            flags += "-"
            flags += "B" if record.p & 0x10 else "-"
            flags += "D" if record.p & 0x08 else "-"
            flags += "I" if record.p & 0x04 else "-"
            flags += "Z" if record.p & 0x02 else "-"
            flags += "C" if record.p & 0x01 else "-"

            instr = f"{record.mnemonic} {record.operand}"
            lines.append(
                f"{record.seq:6d} {record.pc:04X}   {instr:<16} "
                f"{record.a:02X}   {record.x:02X}   {record.y:02X}   {record.sp:02X}   {flags}"
            )

        if len(records) > limit:
            lines.append(f"... and {len(records) - limit} more instructions")

        return "\n".join(lines)

    @staticmethod
    def format_call_tree(result: Any, indent: int = 0) -> str:
        """Format call tree as indented text."""
        return str(result.format_tree())


class MarkdownFormatter:
    """Markdown output formatter."""

    @staticmethod
    def format_trace(records: list[Any], symbols: Any = None, limit: int = 50) -> str:
        """Format trace records as markdown table."""
        lines = []
        lines.append("| # | Addr | Instruction | A | X | Y | SP | Flags |")
        lines.append("|---|------|-------------|---|---|---|----|----- |")

        for record in records[:limit]:
            flags = ""
            flags += "N" if record.p & 0x80 else "-"
            flags += "V" if record.p & 0x40 else "-"
            flags += "-"
            flags += "B" if record.p & 0x10 else "-"
            flags += "D" if record.p & 0x08 else "-"
            flags += "I" if record.p & 0x04 else "-"
            flags += "Z" if record.p & 0x02 else "-"
            flags += "C" if record.p & 0x01 else "-"

            instr = f"{record.mnemonic} {record.operand}"
            lines.append(
                f"| {record.seq} | {record.pc:04X} | {instr} | "
                f"{record.a:02X} | {record.x:02X} | {record.y:02X} | {record.sp:02X} | {flags} |"
            )

        return "\n".join(lines)

    @staticmethod
    def format_call_tree(result: Any) -> str:
        """Format call tree as markdown."""
        lines = ["```"]
        lines.append(result.format_tree())
        lines.append("```")
        return "\n".join(lines)

    @staticmethod
    def format_profile(profile: dict[int, dict[str, Any]], symbols: Any = None) -> str:
        """Format profile as markdown table."""
        lines = []
        lines.append("| Target | Calls | Cycles | Avg Cycles |")
        lines.append("|--------|-------|--------|------------|")

        for target, data in sorted(profile.items(), key=lambda x: -x[1]["total_cycles"]):
            name = f"${target:04X}"
            if symbols:
                sym = symbols.lookup(target)
                if sym:
                    name = sym.name
            avg = data["total_cycles"] // data["call_count"] if data["call_count"] else 0
            lines.append(f"| {name} | {data['call_count']} | {data['total_cycles']} | {avg} |")

        return "\n".join(lines)


class LLMPromptFormatter:
    """
    Generates structured prompts for LLM analysis.

    Designed to provide context and structured data that helps
    LLMs understand and analyze Apple II code execution.
    """

    @staticmethod
    def format_trace_analysis(
        records: list[Any],
        call_result: Any = None,
        symbols: Any = None,
        context: str = "",
        questions: list[str] | None = None,
    ) -> str:
        """Generate an LLM-ready analysis prompt."""
        lines = []

        # Header
        lines.append("# Apple II Execution Trace Analysis")
        lines.append("")

        # Context
        if context:
            lines.append("## Context")
            lines.append(context)
            lines.append("")

        # System description
        lines.append("## System Information")
        lines.append("- CPU: MOS 6502 (8-bit, 1 MHz)")
        lines.append("- Memory: 64KB address space")
        lines.append("- ROM: $D000-$FFFF contains AppleSoft BASIC and Monitor")
        lines.append("- Zero Page: $00-$FF for fast access variables")
        lines.append("- Stack: $0100-$01FF")
        lines.append("- Screen: $0400-$07FF (text page 1)")
        lines.append("")

        # Register descriptions
        lines.append("## CPU Registers")
        lines.append("- A: Accumulator (8-bit, main arithmetic register)")
        lines.append("- X, Y: Index registers (8-bit)")
        lines.append("- SP: Stack pointer (8-bit, offsets from $0100)")
        lines.append("- Flags: N=Negative, V=Overflow, B=Break, D=Decimal, I=Interrupt, Z=Zero, C=Carry")
        lines.append("")

        # Trace excerpt
        lines.append("## Execution Trace")
        lines.append("")
        trace_limit = min(50, len(records))
        lines.append(MarkdownFormatter.format_trace(records, symbols, trace_limit))
        lines.append("")

        if len(records) > trace_limit:
            lines.append(f"*Showing first {trace_limit} of {len(records)} instructions*")
            lines.append("")

        # Call hierarchy if available
        if call_result and call_result.calls:
            lines.append("## Call Hierarchy")
            lines.append("")
            lines.append(MarkdownFormatter.format_call_tree(call_result))
            lines.append("")
            lines.append(f"- Maximum call depth: {call_result.max_depth}")
            lines.append(f"- Total subroutine calls: {call_result.total_calls}")
            if call_result.anomalies:
                lines.append(f"- Stack anomalies: {len(call_result.anomalies)}")
            lines.append("")

        # Key symbols reference
        if symbols:
            lines.append("## Key Symbols Reference")
            lines.append("")
            lines.append("| Address | Name | Type | Description |")
            lines.append("|---------|------|------|-------------|")

            # Extract unique addresses from trace
            trace_addrs = set(r.pc for r in records)

            # Add called addresses
            if call_result:
                for call in call_result.calls:
                    trace_addrs.add(call.frame.target_pc)

            for addr in sorted(trace_addrs):
                sym = symbols.lookup(addr)
                if sym:
                    comment = sym.comment or ""
                    lines.append(f"| ${addr:04X} | {sym.name} | {sym.type} | {comment} |")

            lines.append("")

        # Analysis questions
        lines.append("## Analysis Questions")
        lines.append("")

        if questions:
            for i, q in enumerate(questions, 1):
                lines.append(f"{i}. {q}")
        else:
            lines.append("1. What is the overall purpose of this code sequence?")
            lines.append("2. What subroutines are being called and what do they do?")
            lines.append("3. What data structures or memory locations are being accessed?")
            lines.append("4. Are there any loops or conditional branches? What do they control?")
            lines.append("5. What I/O operations are performed (screen, keyboard, etc.)?")

        lines.append("")
        lines.append("---")
        lines.append("*Please analyze the trace and answer the questions above.*")

        return "\n".join(lines)

    @staticmethod
    def format_routine_analysis(routine_addr: int, records: list[Any], symbols: Any = None, context: str = "") -> str:
        """Generate a prompt for analyzing a specific routine."""
        lines = []

        name = f"${routine_addr:04X}"
        if symbols:
            sym = symbols.lookup(routine_addr)
            if sym:
                name = f"{sym.name} (${routine_addr:04X})"

        lines.append(f"# Analysis of Routine: {name}")
        lines.append("")

        if context:
            lines.append("## Context")
            lines.append(context)
            lines.append("")

        # Filter records for this routine
        routine_records = [r for r in records if r.pc == routine_addr or (routine_addr <= r.pc <= routine_addr + 0x100)]

        lines.append("## Disassembly")
        lines.append("")
        lines.append("```")
        for record in routine_records[:100]:
            lines.append(record.to_text(symbols))
        lines.append("```")
        lines.append("")

        lines.append("## Analysis Tasks")
        lines.append("")
        lines.append("1. Describe what this routine does")
        lines.append("2. Identify input parameters (registers, memory)")
        lines.append("3. Identify output/return values")
        lines.append("4. List subroutines called")
        lines.append("5. Identify any loops and their purpose")
        lines.append("6. Note any side effects (memory modified, I/O)")

        return "\n".join(lines)

    @staticmethod
    def format_boot_sequence_analysis(records: list[Any], call_result: Any = None, symbols: Any = None) -> str:
        """Generate a prompt for analyzing boot sequence."""
        context = """This trace captures the Apple II boot sequence from power-on reset.
The CPU starts execution at the address stored in the RESET vector ($FFFC-$FFFD).
The boot sequence typically:
1. Initializes hardware (display mode, I/O)
2. Clears screen (HOME routine)
3. Sounds the bell
4. Enters the AppleSoft BASIC interpreter
5. Displays the ']' prompt"""

        questions = [
            "What initialization steps are performed during boot?",
            "Which hardware components are configured (display, keyboard, etc.)?",
            "What is the role of each major subroutine in the boot process?",
            "When does control transfer from Monitor ROM to AppleSoft BASIC?",
            "What memory locations are initialized and what are their purposes?",
        ]

        return LLMPromptFormatter.format_trace_analysis(records, call_result, symbols, context, questions)


class JSONLFormatter:
    """JSONL (JSON Lines) formatter for streaming/piping."""

    @staticmethod
    def format_records(records: list[Any]) -> str:
        """Format records as JSONL."""
        return "\n".join(r.to_json() for r in records)

    @staticmethod
    def format_analysis(result: Any, metadata: dict[str, Any] | None = None) -> str:
        """Format analysis result as JSONL with metadata header."""
        lines = []

        if metadata:
            lines.append(json.dumps({"type": "metadata", **metadata}))

        for call in result.calls:
            lines.append(json.dumps({"type": "call", **call.to_dict()}))

        lines.append(
            json.dumps(
                {
                    "type": "summary",
                    "max_depth": result.max_depth,
                    "total_calls": result.total_calls,
                    "anomalies": len(result.anomalies),
                }
            )
        )

        return "\n".join(lines)


# CLI support
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Format Apple II traces")
    parser.add_argument("trace_file", nargs="?", help="Input trace file")
    parser.add_argument(
        "-f", "--format", choices=["text", "markdown", "llm", "jsonl"], default="llm", help="Output format"
    )
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("--boot", action="store_true", help="Analyze boot sequence")
    parser.add_argument("-n", "--limit", type=int, default=100, help="Limit trace lines")

    args = parser.parse_args()

    from tools.trace_logger import TraceLogger, CPUTracer
    from tools.stack_analyzer import StackAnalyzer
    from tools.symbol_table import SymbolTable

    symbols = SymbolTable.with_builtins()

    if args.trace_file:
        logger = TraceLogger.load(args.trace_file)
        records = logger.get_records()
    else:
        # Generate trace
        import cpu_mpu6502
        import memory as mem_module

        memory = mem_module.ObservableMemory()
        rom_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "bin", "A2SOFT2.BIN")
        with open(rom_path, "rb") as rom_f:
            rom_data = rom_f.read()
            for i, byte in enumerate(rom_data):
                memory[0xD000 + i] = byte

        cpu = cpu_mpu6502.MPU(memory)
        cpu.reset()

        tracer = CPUTracer(cpu, memory, symbols)
        tracer.start()

        for _ in range(100000):
            cpu.step()

        tracer.stop()
        records = tracer.get_records()

    # Analyze
    analyzer = StackAnalyzer(symbols=symbols)
    call_result = analyzer.analyze(records)

    # Format
    if args.format == "text":
        output = TextFormatter.format_trace(records, symbols, args.limit)
    elif args.format == "markdown":
        output = MarkdownFormatter.format_trace(records, symbols, args.limit)
        output += "\n\n" + MarkdownFormatter.format_call_tree(call_result)
    elif args.format == "llm":
        if args.boot:
            output = LLMPromptFormatter.format_boot_sequence_analysis(records[: args.limit], call_result, symbols)
        else:
            output = LLMPromptFormatter.format_trace_analysis(records[: args.limit], call_result, symbols)
    else:
        output = JSONLFormatter.format_records(records[: args.limit])

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Wrote formatted output to {args.output}")
    else:
        print(output)
