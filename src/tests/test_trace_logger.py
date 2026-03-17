"""
Tests for trace_logger module.

TDD: These tests are written first, before the implementation.
"""

import unittest
import json
import tempfile
import os


class TestTraceRecord(unittest.TestCase):
    """Tests for TraceRecord dataclass."""

    def test_create_trace_record(self):
        """Can create a trace record."""
        from tools.trace_logger import TraceRecord

        record = TraceRecord(
            seq=1,
            cycle=100,
            pc=0xFA62,
            opcode=0xA9,
            mnemonic="LDA",
            operand="#$00",
            a=0x00,
            x=0x00,
            y=0x00,
            sp=0xFF,
            p=0x34,
        )
        self.assertEqual(record.seq, 1)
        self.assertEqual(record.pc, 0xFA62)
        self.assertEqual(record.mnemonic, "LDA")

    def test_trace_record_to_dict(self):
        """TraceRecord can be converted to dict."""
        from tools.trace_logger import TraceRecord

        record = TraceRecord(
            seq=1,
            cycle=100,
            pc=0xFA62,
            opcode=0xA9,
            mnemonic="LDA",
            operand="#$00",
            a=0x00,
            x=0x00,
            y=0x00,
            sp=0xFF,
            p=0x34,
        )
        d = record.to_dict()
        self.assertEqual(d["seq"], 1)
        self.assertEqual(d["pc"], "FA62")
        self.assertEqual(d["mnemonic"], "LDA")

    def test_trace_record_to_json(self):
        """TraceRecord can be serialized to JSON."""
        from tools.trace_logger import TraceRecord

        record = TraceRecord(
            seq=1,
            cycle=100,
            pc=0xFA62,
            opcode=0xA9,
            mnemonic="LDA",
            operand="#$00",
            a=0x00,
            x=0x00,
            y=0x00,
            sp=0xFF,
            p=0x34,
        )
        json_str = record.to_json()
        d = json.loads(json_str)
        self.assertEqual(d["mnemonic"], "LDA")

    def test_trace_record_to_text(self):
        """TraceRecord can be formatted as text."""
        from tools.trace_logger import TraceRecord

        record = TraceRecord(
            seq=1,
            cycle=100,
            pc=0xFA62,
            opcode=0xA9,
            mnemonic="LDA",
            operand="#$00",
            a=0x42,
            x=0x10,
            y=0x20,
            sp=0xFF,
            p=0x34,
        )
        text = record.to_text()
        self.assertIn("FA62", text)
        self.assertIn("LDA", text)
        self.assertIn("#$00", text)

    def test_trace_record_with_memory_access(self):
        """TraceRecord can include memory access info."""
        from tools.trace_logger import TraceRecord

        record = TraceRecord(
            seq=1,
            cycle=100,
            pc=0xFA64,
            opcode=0x85,
            mnemonic="STA",
            operand="$00",
            a=0x42,
            x=0x00,
            y=0x00,
            sp=0xFF,
            p=0x34,
            mem_addr=0x0000,
            mem_value=0x42,
        )
        d = record.to_dict()
        self.assertEqual(d["mem_addr"], "0000")
        self.assertEqual(d["mem_value"], "42")


class TestTraceLogger(unittest.TestCase):
    """Tests for TraceLogger class."""

    def setUp(self):
        """Set up test fixtures with a mock CPU/runtime."""
        from tools.trace_logger import TraceLogger

        # Create a minimal mock memory
        self.memory = [0] * 0x10000

        # Load a simple program: LDA #$42, STA $00, RTS
        self.memory[0x0300] = 0xA9  # LDA
        self.memory[0x0301] = 0x42  # #$42
        self.memory[0x0302] = 0x85  # STA
        self.memory[0x0303] = 0x00  # $00
        self.memory[0x0304] = 0x60  # RTS

        self.logger = TraceLogger(self.memory)

    def test_create_trace_logger(self):
        """Can create a trace logger."""
        from tools.trace_logger import TraceLogger

        logger = TraceLogger(self.memory)
        self.assertIsNotNone(logger)

    def test_log_instruction(self):
        """Can log a single instruction."""
        record = self.logger.log_instruction(pc=0x0300, a=0x00, x=0x00, y=0x00, sp=0xFF, p=0x34, cycle=0)
        self.assertEqual(record.pc, 0x0300)
        self.assertEqual(record.mnemonic, "LDA")
        self.assertEqual(record.operand, "#$42")

    def test_trace_sequence_number_increments(self):
        """Sequence number increments with each trace."""
        r1 = self.logger.log_instruction(0x0300, 0, 0, 0, 0xFF, 0x34, 0)
        r2 = self.logger.log_instruction(0x0302, 0x42, 0, 0, 0xFF, 0x34, 2)
        self.assertEqual(r1.seq, 1)
        self.assertEqual(r2.seq, 2)

    def test_get_all_records(self):
        """Can retrieve all logged records."""
        self.logger.log_instruction(0x0300, 0, 0, 0, 0xFF, 0x34, 0)
        self.logger.log_instruction(0x0302, 0x42, 0, 0, 0xFF, 0x34, 2)

        records = self.logger.get_records()
        self.assertEqual(len(records), 2)

    def test_clear_records(self):
        """Can clear all logged records."""
        self.logger.log_instruction(0x0300, 0, 0, 0, 0xFF, 0x34, 0)
        self.logger.clear()

        records = self.logger.get_records()
        self.assertEqual(len(records), 0)

    def test_filter_by_address_range(self):
        """Can filter records by address range."""
        self.logger.log_instruction(0x0300, 0, 0, 0, 0xFF, 0x34, 0)
        self.logger.log_instruction(0xFDED, 0, 0, 0, 0xFF, 0x34, 10)

        rom_records = self.logger.filter_by_range(0xF000, 0xFFFF)
        self.assertEqual(len(rom_records), 1)
        self.assertEqual(rom_records[0].pc, 0xFDED)

    def test_filter_by_mnemonic(self):
        """Can filter records by mnemonic."""
        self.logger.log_instruction(0x0300, 0, 0, 0, 0xFF, 0x34, 0)
        self.logger.log_instruction(0x0302, 0x42, 0, 0, 0xFF, 0x34, 2)

        lda_records = self.logger.filter_by_mnemonic("LDA")
        self.assertEqual(len(lda_records), 1)
        self.assertEqual(lda_records[0].mnemonic, "LDA")

    def test_export_to_jsonl(self):
        """Can export records to JSONL format."""
        self.logger.log_instruction(0x0300, 0, 0, 0, 0xFF, 0x34, 0)
        self.logger.log_instruction(0x0302, 0x42, 0, 0, 0xFF, 0x34, 2)

        jsonl = self.logger.to_jsonl()
        lines = jsonl.strip().split("\n")
        self.assertEqual(len(lines), 2)

        # Each line should be valid JSON
        for line in lines:
            d = json.loads(line)
            self.assertIn("mnemonic", d)

    def test_save_to_file(self):
        """Can save records to a file."""
        self.logger.log_instruction(0x0300, 0, 0, 0, 0xFF, 0x34, 0)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            temp_path = f.name

        try:
            self.logger.save(temp_path)

            with open(temp_path) as f:
                content = f.read()

            self.assertIn("LDA", content)
        finally:
            os.unlink(temp_path)

    def test_load_from_file(self):
        """Can load records from a file."""
        from tools.trace_logger import TraceLogger

        # Create a test file
        records_json = [
            {
                "seq": 1,
                "cycle": 0,
                "pc": "0300",
                "op": "A9",
                "mnemonic": "LDA",
                "operand": "#$42",
                "a": "00",
                "x": "00",
                "y": "00",
                "sp": "FF",
                "p": "34",
            },
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for r in records_json:
                f.write(json.dumps(r) + "\n")
            temp_path = f.name

        try:
            loaded = TraceLogger.load(temp_path)
            records = loaded.get_records()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].mnemonic, "LDA")
        finally:
            os.unlink(temp_path)


class TestTraceLoggerWithSymbols(unittest.TestCase):
    """Tests for TraceLogger with symbol table integration."""

    def setUp(self):
        """Set up test fixtures."""
        from tools.trace_logger import TraceLogger
        from tools.symbol_table import SymbolTable

        self.memory = [0] * 0x10000
        # JSR COUT
        self.memory[0x0300] = 0x20  # JSR
        self.memory[0x0301] = 0xED  # low byte
        self.memory[0x0302] = 0xFD  # high byte = $FDED

        self.symbols = SymbolTable.with_builtins()
        self.logger = TraceLogger(self.memory, symbols=self.symbols)

    def test_trace_with_symbols(self):
        """Trace shows symbol names when available."""
        record = self.logger.log_instruction(pc=0x0300, a=0, x=0, y=0, sp=0xFF, p=0x34, cycle=0)
        # The operand should reference COUT
        self.assertIn("FDED", record.operand)

    def test_format_with_symbols(self):
        """Text format shows symbol names."""
        record = self.logger.log_instruction(pc=0x0300, a=0, x=0, y=0, sp=0xFF, p=0x34, cycle=0)
        text = record.to_text(self.symbols)
        self.assertIn("COUT", text)


class TestAddressFilter(unittest.TestCase):
    """Tests for address filtering."""

    def test_create_range_filter(self):
        """Can create an address range filter."""
        from tools.trace_logger import AddressFilter

        f = AddressFilter.range(0xD000, 0xFFFF)
        self.assertTrue(f(0xFDED))
        self.assertFalse(f(0x0300))

    def test_create_exclude_filter(self):
        """Can create an exclusion filter."""
        from tools.trace_logger import AddressFilter

        f = AddressFilter.exclude(0xD000, 0xFFFF)
        self.assertFalse(f(0xFDED))
        self.assertTrue(f(0x0300))

    def test_create_specific_addresses_filter(self):
        """Can create a filter for specific addresses."""
        from tools.trace_logger import AddressFilter

        f = AddressFilter.only([0xFDED, 0xFC58])
        self.assertTrue(f(0xFDED))
        self.assertTrue(f(0xFC58))
        self.assertFalse(f(0x0300))


class TestMnemonicFilter(unittest.TestCase):
    """Tests for mnemonic filtering."""

    def test_create_mnemonic_filter(self):
        """Can create a mnemonic filter."""
        from tools.trace_logger import MnemonicFilter

        f = MnemonicFilter(["JSR", "RTS", "JMP"])
        self.assertTrue(f("JSR"))
        self.assertTrue(f("RTS"))
        self.assertFalse(f("LDA"))

    def test_create_branch_filter(self):
        """Can create a filter for branch instructions."""
        from tools.trace_logger import MnemonicFilter

        f = MnemonicFilter.branches()
        self.assertTrue(f("BEQ"))
        self.assertTrue(f("BNE"))
        self.assertTrue(f("JMP"))
        self.assertFalse(f("LDA"))

    def test_create_call_filter(self):
        """Can create a filter for call/return instructions."""
        from tools.trace_logger import MnemonicFilter

        f = MnemonicFilter.calls()
        self.assertTrue(f("JSR"))
        self.assertTrue(f("RTS"))
        self.assertTrue(f("RTI"))
        self.assertFalse(f("LDA"))


class TestLiveTracing(unittest.TestCase):
    """Tests for live tracing with CPU hooks."""

    def test_create_cpu_tracer(self):
        """Can create a CPU tracer that hooks into execution."""
        from tools.trace_logger import CPUTracer
        import cpu_mpu6502
        import memory

        mem = memory.ObservableMemory()
        # Simple program
        mem[0x0300] = 0xEA  # NOP
        mem[0x0301] = 0xEA  # NOP
        mem[0x0302] = 0x00  # BRK

        cpu = cpu_mpu6502.MPU(mem)
        cpu.pc = 0x0300

        tracer = CPUTracer(cpu, mem)
        tracer.start()

        # Execute a few instructions
        cpu.step()
        cpu.step()

        tracer.stop()

        records = tracer.get_records()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].mnemonic, "NOP")


if __name__ == "__main__":
    unittest.main()
