"""
Routine detector for 6502 execution traces.

Detects subroutine boundaries, builds basic blocks, finds loops,
and constructs routine-level analysis from TraceRecord data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BasicBlock:
    """A sequence of instructions with one entry and one exit."""

    start_addr: int
    end_addr: int
    instructions: list[Any]  # TraceRecord list
    successors: list[int] = field(default_factory=list)  # successor block addresses
    predecessors: list[int] = field(default_factory=list)  # predecessor block addresses


@dataclass
class Routine:
    """A detected subroutine."""

    entry_addr: int
    name: str | None
    blocks: list[BasicBlock]  # BasicBlock list
    calls: set[int]  # JSR target addresses
    callers: set[int]  # addresses that call this routine
    loops: list[tuple[int, int]]  # (header_addr, back_edge_addr) pairs
    instruction_count: int
    cycle_count: int


# Branch/jump mnemonics that end a basic block
_BRANCH_MNEMONICS = {
    "BCC",
    "BCS",
    "BEQ",
    "BMI",
    "BNE",
    "BPL",
    "BVC",
    "BVS",
}
_JUMP_MNEMONICS = {"JMP"}
_TERMINATOR_MNEMONICS = {"RTS", "RTI", "BRK"}
_CALL_MNEMONICS = {"JSR"}

# All mnemonics that change control flow
_CONTROL_FLOW = _BRANCH_MNEMONICS | _JUMP_MNEMONICS | _TERMINATOR_MNEMONICS | _CALL_MNEMONICS

_ADDR_RE = re.compile(r"\$([0-9A-Fa-f]{4})")


def _parse_target(operand: str) -> int | None:
    """Extract target address from operand string like '$FDED' or '$0302'."""
    m = _ADDR_RE.search(operand)
    return int(m.group(1), 16) if m else None


class RoutineDetector:
    """Detects routines and control flow from execution traces."""

    def __init__(self, symbols: Any = None) -> None:
        self.symbols = symbols

    def find_entry_points(self, records: list[Any]) -> set[int]:
        """Find all JSR targets as potential subroutine entry points.

        Returns set of target addresses.
        """
        entries = set()
        for rec in records:
            if rec.mnemonic == "JSR":
                target = _parse_target(rec.operand)
                if target is not None:
                    entries.add(target)
        return entries

    def build_basic_blocks(self, records: list[Any]) -> list[BasicBlock]:
        """Build basic blocks from a sequence of trace records.

        A new block starts when:
        - The address is a branch/jump target
        - The previous instruction was a branch/jump/RTS

        Returns list of BasicBlock objects.
        """
        if not records:
            return []

        # Collect all branch/jump targets and the addresses after branches
        leaders = {records[0].pc}  # First instruction is always a leader
        for rec in records:
            if rec.mnemonic in _BRANCH_MNEMONICS:
                target = _parse_target(rec.operand)
                if target is not None:
                    leaders.add(target)
                # Fall-through address (next instruction)
                # We'll detect this from the trace sequence
            elif rec.mnemonic in _JUMP_MNEMONICS | _TERMINATOR_MNEMONICS:
                pass  # Next instruction (if any) is a new leader

        # Also mark the instruction after any control flow as a leader
        for i in range(len(records) - 1):
            if records[i].mnemonic in (_BRANCH_MNEMONICS | _JUMP_MNEMONICS | _TERMINATOR_MNEMONICS | _CALL_MNEMONICS):
                leaders.add(records[i + 1].pc)

        # Build blocks by walking unique addresses in execution order
        # Deduplicate: keep first occurrence of each PC to avoid loop repeats
        seen_pcs = set()
        unique_records = []
        for rec in records:
            if rec.pc not in seen_pcs:
                seen_pcs.add(rec.pc)
                unique_records.append(rec)

        blocks: list[BasicBlock] = []
        current_instructions: list[Any] = []
        current_start: int | None = None

        for rec in unique_records:
            if rec.pc in leaders and current_instructions:
                # End current block, start new one
                assert current_start is not None
                block = BasicBlock(
                    start_addr=current_start,
                    end_addr=current_instructions[-1].pc,
                    instructions=current_instructions,
                )
                blocks.append(block)
                current_instructions = []
                current_start = None

            if current_start is None:
                current_start = rec.pc
            current_instructions.append(rec)

        # Final block
        if current_instructions:
            assert current_start is not None
            blocks.append(
                BasicBlock(
                    start_addr=current_start,
                    end_addr=current_instructions[-1].pc,
                    instructions=current_instructions,
                )
            )

        # Build successor/predecessor relationships
        block_by_start = {b.start_addr: b for b in blocks}
        for block in blocks:
            last = block.instructions[-1]
            if last.mnemonic in _BRANCH_MNEMONICS:
                target = _parse_target(last.operand)
                if target is not None and target in block_by_start:
                    block.successors.append(target)
                # Fall-through: find the block that starts right after
                for b2 in blocks:
                    if b2.start_addr > block.end_addr:
                        block.successors.append(b2.start_addr)
                        break
            elif last.mnemonic in _JUMP_MNEMONICS:
                target = _parse_target(last.operand)
                if target is not None and target in block_by_start:
                    block.successors.append(target)
            elif last.mnemonic not in _TERMINATOR_MNEMONICS:
                # Straight-line flow to next block
                for b2 in blocks:
                    if b2.start_addr > block.end_addr:
                        block.successors.append(b2.start_addr)
                        break

            # Build predecessors
            for succ_addr in block.successors:
                if succ_addr in block_by_start:
                    block_by_start[succ_addr].predecessors.append(block.start_addr)

        return blocks

    def detect_loops(self, blocks: list[BasicBlock]) -> list[tuple[int, int]]:
        """Detect loops via back-edge detection in the CFG.

        A back-edge is an edge from block B to block A where A dominates B
        (simplified: A.start_addr <= B.start_addr, i.e., A appears earlier).

        Returns list of (header_addr, back_edge_source_addr) tuples.
        """
        loops = []
        for block in blocks:
            for succ in block.successors:
                if succ <= block.start_addr:
                    loops.append((succ, block.start_addr))
        return loops

    def detect_from_trace(self, records: list[Any]) -> list[Routine]:
        """Detect routines from an execution trace.

        Uses JSR/RTS pairs to identify subroutine boundaries,
        then builds basic blocks and detects loops for each.

        Returns list of Routine objects.
        """
        entry_points = self.find_entry_points(records)
        if not entry_points:
            return []

        # Build caller -> callee relationships
        callers_map: dict[int, set[int]] = {}  # entry_addr -> set of caller PCs
        for rec in records:
            if rec.mnemonic == "JSR":
                target = _parse_target(rec.operand)
                if target is not None:
                    callers_map.setdefault(target, set()).add(rec.pc)

        # Extract instructions for each routine from JSR/RTS pairs
        # Track which instructions belong to which routine
        routines = []
        for entry in sorted(entry_points):
            routine_records = self._extract_routine_records(records, entry)
            if not routine_records:
                continue

            blocks = self.build_basic_blocks(routine_records)
            loops = self.detect_loops(blocks) if blocks else []

            # Find calls made by this routine
            calls = set()
            for rec in routine_records:
                if rec.mnemonic == "JSR":
                    target = _parse_target(rec.operand)
                    if target is not None:
                        calls.add(target)

            name = None
            if self.symbols:
                sym = self.symbols.lookup(entry)
                if sym:
                    name = sym.name

            total_cycles = sum(rec.cycle for rec in routine_records)
            routines.append(
                Routine(
                    entry_addr=entry,
                    name=name,
                    blocks=blocks,
                    calls=calls,
                    callers=callers_map.get(entry, set()),
                    loops=loops,
                    instruction_count=len(routine_records),
                    cycle_count=total_cycles,
                )
            )

        return routines

    def _extract_routine_records(self, records: list[Any], entry_addr: int) -> list[Any]:
        """Extract trace records belonging to a routine.

        Collects instructions from entry_addr until the matching RTS,
        excluding nested subroutine calls.
        """
        result = []
        depth = 0
        recording = False

        for rec in records:
            if not recording:
                if rec.pc == entry_addr:
                    recording = True
                    depth = 0
                else:
                    continue

            if recording:
                if rec.mnemonic == "JSR" and depth == 0 and rec.pc != entry_addr:
                    # Entering a nested call — collect the JSR but skip the callee
                    result.append(rec)
                    depth += 1
                elif rec.mnemonic == "JSR" and depth > 0:
                    depth += 1
                elif rec.mnemonic in ("RTS", "RTI") and depth > 0:
                    depth -= 1
                elif rec.mnemonic in ("RTS", "RTI") and depth == 0:
                    result.append(rec)
                    break
                elif depth == 0:
                    result.append(rec)

        return result
