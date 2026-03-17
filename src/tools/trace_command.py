#!/usr/bin/env python3
"""
Trace a BASIC command execution on Apple II.

Usage:
    python -m tools.trace_command 'PRINT "HELLO WORLD"'
    python -m tools.trace_command 'PRINT 2+2' --format tree
    python -m tools.trace_command '10 PRINT "HI"' --format llm
"""

from __future__ import annotations

import sys

from headless import headless_boot

from tools.trace_logger import CPUTracer
from tools.stack_analyzer import StackAnalyzer
from tools.symbol_table import SymbolTable
from tools.formatters import TextFormatter, MarkdownFormatter, LLMPromptFormatter


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Trace BASIC command execution on Apple II")
    parser.add_argument("command", help="BASIC command to trace")
    parser.add_argument(
        "-f", "--format", choices=["text", "tree", "profile", "markdown", "llm"], default="text", help="Output format"
    )
    parser.add_argument("-n", "--limit", type=int, default=100, help="Limit trace lines")
    parser.add_argument("--show-screen", action="store_true", help="Show screen after execution")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.verbose:
        print("Booting Apple II...", file=sys.stderr)

    runtime, display, keyboard = headless_boot()

    if not display.has_prompt():
        print("ERROR: Failed to boot to prompt", file=sys.stderr)
        return 1

    symbols = SymbolTable.with_builtins()

    if args.verbose:
        print(f"Typing: {args.command}", file=sys.stderr)

    # Type the command
    keyboard.type_string(args.command)
    initial_prompts = display.count_prompts()

    # Start tracing
    cpu = runtime.cpu
    tracer = CPUTracer(cpu, runtime.bus, symbols)
    tracer.start()

    # Execute until we see a new prompt (command completed)
    exec_steps = 0
    max_exec = 10000000
    while exec_steps < max_exec:
        cpu.step()
        exec_steps += 1
        if exec_steps % 1000 == 0:
            if display.count_prompts() > initial_prompts:
                # Give a few more steps to settle
                for _ in range(1000):
                    cpu.step()
                break

    tracer.stop()
    records = tracer.get_records()

    if args.verbose:
        print(f"Executed {exec_steps} steps, {len(records)} instructions traced", file=sys.stderr)

    # Analyze
    analyzer = StackAnalyzer(symbols=symbols)
    call_result = analyzer.analyze(records)

    # Output
    if args.format == "text":
        print(f"=== Tracing: {args.command} ===")
        print(f"Instructions: {len(records)}, Steps: {exec_steps}")
        print(f"Calls: {call_result.total_calls}, Max depth: {call_result.max_depth}")
        print()
        print(TextFormatter.format_trace(records, symbols, args.limit))
        if call_result.calls:
            print()
            print("=== Call Tree ===")
            print(call_result.format_tree())

    elif args.format == "tree":
        print(f"=== Call Tree for: {args.command} ===")
        print(call_result.format_tree())
        print()
        print(f"Total calls: {call_result.total_calls}")
        print(f"Max depth: {call_result.max_depth}")

    elif args.format == "profile":
        profile = call_result.profile_by_target()
        print(f"=== Profile for: {args.command} ===")
        print(f"{'Target':<20} {'Calls':>6} {'Cycles':>10} {'Avg':>8}")
        print("-" * 50)
        for target, data in sorted(profile.items(), key=lambda x: -x[1]["total_cycles"]):
            name = f"${target:04X}"
            sym = symbols.lookup(target)
            if sym:
                name = sym.name
            avg = data["total_cycles"] // data["call_count"] if data["call_count"] else 0
            print(f"{name:<20} {data['call_count']:>6} {data['total_cycles']:>10} {avg:>8}")

    elif args.format == "markdown":
        print(f"# Execution Trace: `{args.command}`")
        print()
        print(f"- Instructions: {len(records)}")
        print(f"- Total calls: {call_result.total_calls}")
        print(f"- Max depth: {call_result.max_depth}")
        print()
        print("## Trace")
        print()
        print(MarkdownFormatter.format_trace(records, symbols, args.limit))
        if call_result.calls:
            print()
            print("## Call Hierarchy")
            print()
            print(MarkdownFormatter.format_call_tree(call_result))

    elif args.format == "llm":
        context = f"""This trace shows the execution of the AppleSoft BASIC command: {args.command}

The Apple II interprets the command through its BASIC interpreter located in ROM.
Key routines involved typically include:
- GETLN: Get a line of input
- PARSE: Parse the BASIC statement
- PRINT routines for output
- COUT: Character output to screen
"""
        print(
            LLMPromptFormatter.format_trace_analysis(
                records[: args.limit],
                call_result,
                symbols,
                context,
                questions=[
                    f"How does the Apple II execute the '{args.command}' command?",
                    "What routines are involved in parsing and executing this command?",
                    "How is the output generated and displayed on screen?",
                    "What is the flow of control through the BASIC interpreter?",
                    "Are there any interesting optimizations or patterns in the code?",
                ],
            )
        )

    # Show screen if requested
    if args.show_screen:
        print()
        print("=== Screen ===")
        print("-" * 42)
        print("|" + display.get_screen().replace("\n", "|\n|") + "|")
        print("-" * 42)

    return 0


if __name__ == "__main__":
    sys.exit(main())
