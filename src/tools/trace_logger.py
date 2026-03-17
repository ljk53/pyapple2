"""
Trace Logger for Apple II Analysis Toolkit.

Records every instruction executed with full CPU state.
Supports filtering, file output, and integration with symbol tables.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from tools.symbol_table import SymbolTable


@dataclass
class TraceRecord:
    """Represents a single traced instruction."""

    seq: int  # Sequence number
    cycle: int  # CPU cycle count
    pc: int  # Program counter
    opcode: int  # Opcode byte
    mnemonic: str  # Instruction mnemonic
    operand: str  # Operand string
    a: int  # Accumulator
    x: int  # X register
    y: int  # Y register
    sp: int  # Stack pointer
    p: int  # Processor status
    mem_addr: int | None = None  # Memory address accessed
    mem_value: int | None = None  # Memory value read/written
    bytes_: list[int] | None = None  # Instruction bytes

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = {
            "seq": self.seq,
            "cycle": self.cycle,
            "pc": f"{self.pc:04X}",
            "op": f"{self.opcode:02X}",
            "mnemonic": self.mnemonic,
            "operand": self.operand,
            "a": f"{self.a:02X}",
            "x": f"{self.x:02X}",
            "y": f"{self.y:02X}",
            "sp": f"{self.sp:02X}",
            "p": f"{self.p:02X}",
        }
        if self.mem_addr is not None:
            d["mem_addr"] = f"{self.mem_addr:04X}"
        if self.mem_value is not None:
            d["mem_value"] = f"{self.mem_value:02X}"
        if self.bytes_:
            d["bytes"] = [f"{b:02X}" for b in self.bytes_]
        return d

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    def to_text(self, symbols: SymbolTable | None = None) -> str:
        """Format as human-readable text."""
        # Format flags
        flags = ""
        flags += "N" if self.p & 0x80 else "-"
        flags += "V" if self.p & 0x40 else "-"
        flags += "-"  # Unused
        flags += "B" if self.p & 0x10 else "-"
        flags += "D" if self.p & 0x08 else "-"
        flags += "I" if self.p & 0x04 else "-"
        flags += "Z" if self.p & 0x02 else "-"
        flags += "C" if self.p & 0x01 else "-"

        # Format operand with symbols if available
        operand = self.operand
        if symbols and self.operand:
            # Try to find symbols in operand
            import re

            match = re.search(r"\$([0-9A-F]{4})", operand)
            if match:
                addr = int(match.group(1), 16)
                sym = symbols.lookup(addr)
                if sym:
                    operand = operand.replace(f"${match.group(1)}", f"{sym.name}")

        return (
            f"{self.seq:6d} {self.pc:04X}: {self.mnemonic:4s} {operand:12s} "
            f"A={self.a:02X} X={self.x:02X} Y={self.y:02X} SP={self.sp:02X} {flags}"
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TraceRecord:
        """Create from dictionary."""
        return cls(
            seq=d["seq"],
            cycle=d["cycle"],
            pc=int(d["pc"], 16),
            opcode=int(d["op"], 16),
            mnemonic=d["mnemonic"],
            operand=d.get("operand", ""),
            a=int(d["a"], 16),
            x=int(d["x"], 16),
            y=int(d["y"], 16),
            sp=int(d["sp"], 16),
            p=int(d["p"], 16),
            mem_addr=int(d["mem_addr"], 16) if "mem_addr" in d else None,
            mem_value=int(d["mem_value"], 16) if "mem_value" in d else None,
        )


class MinimalDisassembler:
    """Minimal disassembler that works with raw memory."""

    # Opcode table: (length, mnemonic, addressing_mode)
    OPCODES = {
        0x00: (1, "BRK", None),
        0x01: (2, "ORA", "indx"),
        0x05: (2, "ORA", "zp"),
        0x06: (2, "ASL", "zp"),
        0x08: (1, "PHP", None),
        0x09: (2, "ORA", "imm"),
        0x0A: (1, "ASL", None),
        0x0D: (3, "ORA", "abs"),
        0x0E: (3, "ASL", "abs"),
        0x10: (2, "BPL", "rel"),
        0x11: (2, "ORA", "indy"),
        0x15: (2, "ORA", "zpx"),
        0x16: (2, "ASL", "zpx"),
        0x18: (1, "CLC", None),
        0x19: (3, "ORA", "absy"),
        0x1D: (3, "ORA", "absx"),
        0x1E: (3, "ASL", "absx"),
        0x20: (3, "JSR", "abs"),
        0x21: (2, "AND", "indx"),
        0x24: (2, "BIT", "zp"),
        0x25: (2, "AND", "zp"),
        0x26: (2, "ROL", "zp"),
        0x28: (1, "PLP", None),
        0x29: (2, "AND", "imm"),
        0x2A: (1, "ROL", None),
        0x2C: (3, "BIT", "abs"),
        0x2D: (3, "AND", "abs"),
        0x2E: (3, "ROL", "abs"),
        0x30: (2, "BMI", "rel"),
        0x31: (2, "AND", "indy"),
        0x35: (2, "AND", "zpx"),
        0x36: (2, "ROL", "zpx"),
        0x38: (1, "SEC", None),
        0x39: (3, "AND", "absy"),
        0x3D: (3, "AND", "absx"),
        0x3E: (3, "ROL", "absx"),
        0x40: (1, "RTI", None),
        0x41: (2, "EOR", "indx"),
        0x45: (2, "EOR", "zp"),
        0x46: (2, "LSR", "zp"),
        0x48: (1, "PHA", None),
        0x49: (2, "EOR", "imm"),
        0x4A: (1, "LSR", None),
        0x4C: (3, "JMP", "abs"),
        0x4D: (3, "EOR", "abs"),
        0x4E: (3, "LSR", "abs"),
        0x50: (2, "BVC", "rel"),
        0x51: (2, "EOR", "indy"),
        0x55: (2, "EOR", "zpx"),
        0x56: (2, "LSR", "zpx"),
        0x58: (1, "CLI", None),
        0x59: (3, "EOR", "absy"),
        0x5D: (3, "EOR", "absx"),
        0x5E: (3, "LSR", "absx"),
        0x60: (1, "RTS", None),
        0x61: (2, "ADC", "indx"),
        0x65: (2, "ADC", "zp"),
        0x66: (2, "ROR", "zp"),
        0x68: (1, "PLA", None),
        0x69: (2, "ADC", "imm"),
        0x6A: (1, "ROR", None),
        0x6C: (3, "JMP", "ind"),
        0x6D: (3, "ADC", "abs"),
        0x6E: (3, "ROR", "abs"),
        0x70: (2, "BVS", "rel"),
        0x71: (2, "ADC", "indy"),
        0x75: (2, "ADC", "zpx"),
        0x76: (2, "ROR", "zpx"),
        0x78: (1, "SEI", None),
        0x79: (3, "ADC", "absy"),
        0x7D: (3, "ADC", "absx"),
        0x7E: (3, "ROR", "absx"),
        0x81: (2, "STA", "indx"),
        0x84: (2, "STY", "zp"),
        0x85: (2, "STA", "zp"),
        0x86: (2, "STX", "zp"),
        0x88: (1, "DEY", None),
        0x8A: (1, "TXA", None),
        0x8C: (3, "STY", "abs"),
        0x8D: (3, "STA", "abs"),
        0x8E: (3, "STX", "abs"),
        0x90: (2, "BCC", "rel"),
        0x91: (2, "STA", "indy"),
        0x94: (2, "STY", "zpx"),
        0x95: (2, "STA", "zpx"),
        0x96: (2, "STX", "zpy"),
        0x98: (1, "TYA", None),
        0x99: (3, "STA", "absy"),
        0x9A: (1, "TXS", None),
        0x9D: (3, "STA", "absx"),
        0xA0: (2, "LDY", "imm"),
        0xA1: (2, "LDA", "indx"),
        0xA2: (2, "LDX", "imm"),
        0xA4: (2, "LDY", "zp"),
        0xA5: (2, "LDA", "zp"),
        0xA6: (2, "LDX", "zp"),
        0xA8: (1, "TAY", None),
        0xA9: (2, "LDA", "imm"),
        0xAA: (1, "TAX", None),
        0xAC: (3, "LDY", "abs"),
        0xAD: (3, "LDA", "abs"),
        0xAE: (3, "LDX", "abs"),
        0xB0: (2, "BCS", "rel"),
        0xB1: (2, "LDA", "indy"),
        0xB4: (2, "LDY", "zpx"),
        0xB5: (2, "LDA", "zpx"),
        0xB6: (2, "LDX", "zpy"),
        0xB8: (1, "CLV", None),
        0xB9: (3, "LDA", "absy"),
        0xBA: (1, "TSX", None),
        0xBC: (3, "LDY", "absx"),
        0xBD: (3, "LDA", "absx"),
        0xBE: (3, "LDX", "absy"),
        0xC0: (2, "CPY", "imm"),
        0xC1: (2, "CMP", "indx"),
        0xC4: (2, "CPY", "zp"),
        0xC5: (2, "CMP", "zp"),
        0xC6: (2, "DEC", "zp"),
        0xC8: (1, "INY", None),
        0xC9: (2, "CMP", "imm"),
        0xCA: (1, "DEX", None),
        0xCC: (3, "CPY", "abs"),
        0xCD: (3, "CMP", "abs"),
        0xCE: (3, "DEC", "abs"),
        0xD0: (2, "BNE", "rel"),
        0xD1: (2, "CMP", "indy"),
        0xD5: (2, "CMP", "zpx"),
        0xD6: (2, "DEC", "zpx"),
        0xD8: (1, "CLD", None),
        0xD9: (3, "CMP", "absy"),
        0xDD: (3, "CMP", "absx"),
        0xDE: (3, "DEC", "absx"),
        0xE0: (2, "CPX", "imm"),
        0xE1: (2, "SBC", "indx"),
        0xE4: (2, "CPX", "zp"),
        0xE5: (2, "SBC", "zp"),
        0xE6: (2, "INC", "zp"),
        0xE8: (1, "INX", None),
        0xE9: (2, "SBC", "imm"),
        0xEA: (1, "NOP", None),
        0xEC: (3, "CPX", "abs"),
        0xED: (3, "SBC", "abs"),
        0xEE: (3, "INC", "abs"),
        0xF0: (2, "BEQ", "rel"),
        0xF1: (2, "SBC", "indy"),
        0xF5: (2, "SBC", "zpx"),
        0xF6: (2, "INC", "zpx"),
        0xF8: (1, "SED", None),
        0xF9: (3, "SBC", "absy"),
        0xFD: (3, "SBC", "absx"),
        0xFE: (3, "INC", "absx"),
    }

    def __init__(self, memory: list[int] | bytearray) -> None:
        self.memory = memory

    def disasm(self, pc: int) -> tuple[str, str, int]:
        """Disassemble instruction at pc, return (mnemonic, operand, length)."""
        opcode = self.memory[pc]
        info = self.OPCODES.get(opcode, (1, "???", None))
        length, mnemonic, mode = info

        operand = ""
        if mode == "imm":
            operand = f"#${self.memory[pc + 1]:02X}"
        elif mode == "zp":
            operand = f"${self.memory[pc + 1]:02X}"
        elif mode == "zpx":
            operand = f"${self.memory[pc + 1]:02X},X"
        elif mode == "zpy":
            operand = f"${self.memory[pc + 1]:02X},Y"
        elif mode == "abs":
            addr = self.memory[pc + 1] + (self.memory[pc + 2] << 8)
            operand = f"${addr:04X}"
        elif mode == "absx":
            addr = self.memory[pc + 1] + (self.memory[pc + 2] << 8)
            operand = f"${addr:04X},X"
        elif mode == "absy":
            addr = self.memory[pc + 1] + (self.memory[pc + 2] << 8)
            operand = f"${addr:04X},Y"
        elif mode == "ind":
            addr = self.memory[pc + 1] + (self.memory[pc + 2] << 8)
            operand = f"(${addr:04X})"
        elif mode == "indx":
            operand = f"(${self.memory[pc + 1]:02X},X)"
        elif mode == "indy":
            operand = f"(${self.memory[pc + 1]:02X}),Y"
        elif mode == "rel":
            offset = self.memory[pc + 1]
            if offset > 0x7F:
                offset = offset - 0x100
            target = pc + 2 + offset
            operand = f"${target:04X}"

        return mnemonic, operand, length


class TraceLogger:
    """
    Logs CPU instruction execution traces.

    Can work with raw memory or integrate with a CPU for live tracing.
    """

    def __init__(self, memory: list[int] | bytearray, symbols: SymbolTable | None = None) -> None:
        """Create a trace logger."""
        self.memory = memory
        self.symbols = symbols
        self.disasm = MinimalDisassembler(memory)
        self._records: list[TraceRecord] = []
        self._seq = 0

    def log_instruction(self, pc: int, a: int, x: int, y: int, sp: int, p: int, cycle: int) -> TraceRecord:
        """Log a single instruction execution."""
        self._seq += 1

        opcode = self.memory[pc]
        mnemonic, operand, length = self.disasm.disasm(pc)
        bytes_ = [self.memory[pc + i] for i in range(length)]

        record = TraceRecord(
            seq=self._seq,
            cycle=cycle,
            pc=pc,
            opcode=opcode,
            mnemonic=mnemonic,
            operand=operand,
            a=a,
            x=x,
            y=y,
            sp=sp,
            p=p,
            bytes_=bytes_,
        )

        self._records.append(record)
        return record

    def get_records(self) -> list[TraceRecord]:
        """Get all logged records."""
        return list(self._records)

    def clear(self) -> None:
        """Clear all logged records."""
        self._records.clear()
        self._seq = 0

    def filter_by_range(self, start: int, end: int) -> list[TraceRecord]:
        """Filter records by address range."""
        return [r for r in self._records if start <= r.pc <= end]

    def filter_by_mnemonic(self, mnemonic: str) -> list[TraceRecord]:
        """Filter records by mnemonic."""
        return [r for r in self._records if r.mnemonic == mnemonic]

    def to_jsonl(self) -> str:
        """Export records to JSONL format."""
        return "\n".join(r.to_json() for r in self._records)

    def save(self, path: str) -> None:
        """Save records to a file."""
        with open(path, "w") as f:
            for record in self._records:
                f.write(record.to_json() + "\n")

    @classmethod
    def load(cls, path: str) -> TraceLogger:
        """Load records from a file."""
        logger = cls([0] * 0x10000)  # Dummy memory
        with open(path) as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    record = TraceRecord.from_dict(d)
                    logger._records.append(record)
                    logger._seq = max(logger._seq, record.seq)
        return logger


class AddressFilter:
    """Factory for address filters."""

    @staticmethod
    def range(start: int, end: int) -> Callable[[int], bool]:
        """Create a filter that accepts addresses in range."""
        return lambda addr: start <= addr <= end

    @staticmethod
    def exclude(start: int, end: int) -> Callable[[int], bool]:
        """Create a filter that excludes addresses in range."""
        return lambda addr: not (start <= addr <= end)

    @staticmethod
    def only(addresses: list[int]) -> Callable[[int], bool]:
        """Create a filter for specific addresses."""
        addr_set = set(addresses)
        return lambda addr: addr in addr_set


class MnemonicFilter:
    """Factory for mnemonic filters."""

    def __init__(self, mnemonics: list[str]) -> None:
        self._mnemonics = set(mnemonics)

    def __call__(self, mnemonic: str) -> bool:
        return mnemonic in self._mnemonics

    @classmethod
    def branches(cls) -> MnemonicFilter:
        """Create filter for branch instructions."""
        return cls(["BCC", "BCS", "BEQ", "BMI", "BNE", "BPL", "BVC", "BVS", "JMP"])

    @classmethod
    def calls(cls) -> MnemonicFilter:
        """Create filter for call/return instructions."""
        return cls(["JSR", "RTS", "RTI", "BRK"])


class CPUTracer:
    """
    Traces CPU execution by hooking into the step function.
    """

    def __init__(self, cpu: Any, memory: Any, symbols: SymbolTable | None = None) -> None:
        """Create a CPU tracer."""
        self.cpu = cpu
        self.memory = memory
        self.symbols = symbols
        self.logger = TraceLogger(memory, symbols)
        self._original_step: Callable[[], None] | None = None
        self._running = False

    def start(self) -> None:
        """Start tracing."""
        if self._running:
            return

        self._original_step = self.cpu.step
        tracer = self

        def traced_step() -> None:
            # Log before step
            pc = tracer.cpu.pc
            a = tracer.cpu.a
            x = tracer.cpu.x
            y = tracer.cpu.y
            sp = tracer.cpu.sp
            p = tracer.cpu.p if hasattr(tracer.cpu, "p") else 0
            cycle = tracer.cpu.processorCycles

            tracer.logger.log_instruction(pc, a, x, y, sp, p, cycle)

            # Execute original step
            assert tracer._original_step is not None
            tracer._original_step()

        self.cpu.step = traced_step
        self._running = True

    def stop(self) -> None:
        """Stop tracing."""
        if self._running and self._original_step:
            self.cpu.step = self._original_step
            self._running = False

    def get_records(self) -> list[TraceRecord]:
        """Get traced records."""
        return self.logger.get_records()

    def clear(self) -> None:
        """Clear traced records."""
        self.logger.clear()


# Standalone CLI support
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Apple II Trace Logger")
    parser.add_argument("-n", "--count", type=int, default=1000, help="Number of instructions to trace")
    parser.add_argument("-o", "--output", metavar="FILE", help="Output file (JSONL format)")
    parser.add_argument("-R", "--rom", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "bin", "A2SOFT2.BIN"), help="ROM file to use")
    parser.add_argument("--range", metavar="START-END", help="Address range filter (e.g., D000-FFFF)")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    parser.add_argument("--boot", action="store_true", help="Trace boot sequence until prompt")

    args = parser.parse_args()

    # Import emulator components
    import cpu_mpu6502
    import memory as mem_module

    # Set up emulator
    memory = mem_module.ObservableMemory()

    # Load ROM
    with open(args.rom, "rb") as rom_f:
        rom_data = rom_f.read()
        for i, byte in enumerate(rom_data):
            memory[0xD000 + i] = byte

    cpu = cpu_mpu6502.MPU(memory)
    cpu.reset()

    # Create tracer
    from tools.symbol_table import SymbolTable as _SymbolTable

    symbols = _SymbolTable.with_builtins()
    tracer = CPUTracer(cpu, memory, symbols)

    # Trace execution
    tracer.start()

    count = 0
    max_count = args.count

    if args.boot:
        # Run until prompt found
        while count < 10000000:
            cpu.step()
            count += 1
            # Check for prompt
            if count % 10000 == 0:
                # Simple check for ']' in screen memory
                for addr in range(0x400, 0x800):
                    if memory[addr] == ord("]") | 0x80:
                        max_count = count
                        break
                else:
                    continue
                break
    else:
        for _ in range(max_count):
            cpu.step()
            count += 1

    tracer.stop()

    # Apply filters
    records = tracer.get_records()

    if args.range:
        start, end = args.range.split("-")
        start = int(start, 16)
        end = int(end, 16)
        records = [r for r in records if start <= r.pc <= end]

    # Output
    if args.output:
        with open(args.output, "w") as f:
            for record in records:
                f.write(record.to_json() + "\n")
        print(f"Wrote {len(records)} records to {args.output}")
    else:
        for record in records:
            if args.format == "text":
                print(record.to_text(symbols))
            else:
                print(record.to_json())
