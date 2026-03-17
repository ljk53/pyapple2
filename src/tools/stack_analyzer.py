"""
Stack Analyzer for Apple II Analysis Toolkit.

Tracks subroutine calls, builds call trees, and profiles execution.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallFrame:
    """Represents an active subroutine call."""

    caller_pc: int  # Address of JSR instruction
    target_pc: int  # Subroutine entry point
    return_addr: int  # Expected return address (JSR + 3)
    entry_sp: int  # Stack pointer at entry
    entry_cycle: int  # Cycle count at entry
    entry_seq: int  # Sequence number at entry


@dataclass
class CallRecord:
    """Represents a completed subroutine call."""

    frame: CallFrame
    exit_cycle: int
    exit_seq: int
    children: list[CallRecord] = field(default_factory=list)
    stack_delta: int = 0  # Net stack change (should be 0 for balanced)

    @property
    def duration(self) -> int:
        """Duration in cycles."""
        return self.exit_cycle - self.frame.entry_cycle

    @property
    def instruction_count(self) -> int:
        """Number of instructions executed."""
        return self.exit_seq - self.frame.entry_seq

    def to_dict(self, symbols: Any = None) -> dict[str, Any]:
        """Convert to dictionary."""
        target_name = None
        if symbols:
            sym = symbols.lookup(self.frame.target_pc)
            if sym:
                target_name = sym.name

        d = {
            "target": f"{self.frame.target_pc:04X}",
            "target_name": target_name,
            "caller": f"{self.frame.caller_pc:04X}",
            "return_addr": f"{self.frame.return_addr:04X}",
            "duration": self.duration,
            "instructions": self.instruction_count,
            "stack_delta": self.stack_delta,
        }
        if self.children:
            d["children"] = [c.to_dict(symbols) for c in self.children]
        return d


@dataclass
class AnalysisResult:
    """Result of stack analysis."""

    calls: list[CallRecord]
    max_depth: int
    total_calls: int
    anomalies: list[dict[str, Any]]
    unclosed_calls: list[CallFrame]
    symbols: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "calls": [c.to_dict(self.symbols) for c in self.calls],
            "max_depth": self.max_depth,
            "total_calls": self.total_calls,
            "anomalies": self.anomalies,
            "unclosed_calls": len(self.unclosed_calls),
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    def format_tree(self, indent: str = "") -> str:
        """Format calls as a tree structure."""
        lines = []

        def format_call(call: CallRecord, prefix: str, is_last: bool) -> None:
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")

            target_name = f"${call.frame.target_pc:04X}"
            if self.symbols:
                sym = self.symbols.lookup(call.frame.target_pc)
                if sym:
                    target_name = f"{sym.name} (${call.frame.target_pc:04X})"

            lines.append(f"{prefix}{connector}{target_name} [{call.duration} cycles]")

            for i, child in enumerate(call.children):
                format_call(child, child_prefix, i == len(call.children) - 1)

        for i, call in enumerate(self.calls):
            format_call(call, "", i == len(self.calls) - 1)

        return "\n".join(lines)

    def profile_by_target(self) -> dict[int, dict[str, Any]]:
        """Profile calls by target address."""
        profile: dict[int, dict[str, Any]] = {}

        def add_call(call: CallRecord) -> None:
            target = call.frame.target_pc
            if target not in profile:
                profile[target] = {
                    "call_count": 0,
                    "total_cycles": 0,
                    "total_instructions": 0,
                }
            profile[target]["call_count"] += 1
            profile[target]["total_cycles"] += call.duration
            profile[target]["total_instructions"] += call.instruction_count

            for child in call.children:
                add_call(child)

        for call in self.calls:
            add_call(call)

        return profile


class StackAnalyzer:
    """
    Analyzes trace records to build call trees and track stack usage.
    """

    def __init__(self, symbols: Any = None) -> None:
        """Create a stack analyzer."""
        self.symbols = symbols

    def analyze(self, records: list[Any]) -> AnalysisResult:
        """Analyze trace records and build call hierarchy."""
        # Stack of active calls
        call_stack: list[CallFrame] = []
        # Root-level completed calls
        root_calls: list[CallRecord] = []
        # Stack of completed calls at each level (for nesting)
        completed_stack: list[list[CallRecord]] = [[]]

        max_depth = 0
        total_calls = 0
        anomalies: list[dict[str, Any]] = []

        for record in records:
            mnemonic = record.mnemonic

            if mnemonic == "JSR":
                # Parse target address from operand
                target = self._parse_address(record.operand)
                if target is None:
                    continue

                # Create call frame
                frame = CallFrame(
                    caller_pc=record.pc,
                    target_pc=target,
                    return_addr=record.pc + 3,  # JSR is 3 bytes
                    entry_sp=record.sp - 2,  # SP after push
                    entry_cycle=record.cycle,
                    entry_seq=record.seq,
                )

                call_stack.append(frame)
                completed_stack.append([])
                total_calls += 1
                max_depth = max(max_depth, len(call_stack))

            elif mnemonic in ("RTS", "RTI"):
                if not call_stack:
                    # RTS without matching JSR
                    anomalies.append(
                        {
                            "type": "unmatched_rts",
                            "pc": record.pc,
                            "seq": record.seq,
                        }
                    )
                    continue

                # Pop the call frame
                frame = call_stack.pop()
                children = completed_stack.pop()

                # Create completed call record
                call_record = CallRecord(
                    frame=frame,
                    exit_cycle=record.cycle,
                    exit_seq=record.seq,
                    children=children,
                    stack_delta=record.sp - frame.entry_sp,
                )

                # Add to parent's children or root
                if call_stack:  # If there's still a parent call
                    completed_stack[-1].append(call_record)
                else:
                    root_calls.append(call_record)

        # Any remaining calls on stack are unclosed
        unclosed_calls = list(call_stack)

        return AnalysisResult(
            calls=root_calls,
            max_depth=max_depth,
            total_calls=total_calls,
            anomalies=anomalies,
            unclosed_calls=unclosed_calls,
            symbols=self.symbols,
        )

    def _parse_address(self, operand: str) -> int | None:
        """Parse address from operand string."""
        if not operand:
            return None

        # Match $XXXX or symbol name
        match = re.search(r"\$([0-9A-Fa-f]{4})", operand)
        if match:
            return int(match.group(1), 16)

        # Try to look up symbol
        if self.symbols:
            sym = self.symbols.lookup_name(operand.strip())
            if sym:
                return int(sym.address)

        return None


# Standalone CLI support
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Apple II Stack Analyzer")
    parser.add_argument("trace_file", nargs="?", help="Trace file (JSONL format)")
    parser.add_argument("-o", "--output", metavar="FILE", help="Output file")
    parser.add_argument("--format", choices=["json", "tree", "profile"], default="tree", help="Output format")
    parser.add_argument("--check-balance", action="store_true", help="Check for stack anomalies")

    args = parser.parse_args()

    from tools.trace_logger import TraceLogger
    from tools.symbol_table import SymbolTable

    symbols = SymbolTable.with_builtins()

    # Load trace
    if args.trace_file:
        logger = TraceLogger.load(args.trace_file)
        records = logger.get_records()
    else:
        # Generate trace from boot
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

        from tools.trace_logger import CPUTracer

        tracer = CPUTracer(cpu, memory, symbols)
        tracer.start()

        # Run until prompt or max cycles
        for _ in range(100000):
            cpu.step()

        tracer.stop()
        records = tracer.get_records()

    # Analyze
    analyzer = StackAnalyzer(symbols=symbols)
    result = analyzer.analyze(records)

    # Output
    if args.format == "json":
        output = result.to_json()
    elif args.format == "tree":
        output = result.format_tree()
        output += f"\n\nMax depth: {result.max_depth}"
        output += f"\nTotal calls: {result.total_calls}"
        if result.unclosed_calls:
            output += f"\nUnclosed calls: {len(result.unclosed_calls)}"
        if result.anomalies:
            output += f"\nAnomalies: {len(result.anomalies)}"
    elif args.format == "profile":
        profile = result.profile_by_target()
        lines = ["Target          Calls   Cycles   Avg"]
        lines.append("-" * 45)
        for target, data in sorted(profile.items(), key=lambda x: -x[1]["total_cycles"]):
            name = f"${target:04X}"
            if symbols:
                sym = symbols.lookup(target)
                if sym:
                    name = f"{sym.name:12s}"
            avg = data["total_cycles"] // data["call_count"] if data["call_count"] else 0
            lines.append(f"{name:<16} {data['call_count']:>5} {data['total_cycles']:>8} {avg:>6}")
        output = "\n".join(lines)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Wrote analysis to {args.output}")
    else:
        print(output)

    if args.check_balance and result.anomalies:
        print(f"\n*** WARNING: {len(result.anomalies)} stack anomalies detected! ***")
        for a in result.anomalies[:5]:
            print(f"  {a['type']} at ${a['pc']:04X} (seq {a['seq']})")
