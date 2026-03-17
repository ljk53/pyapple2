"""
Tests for symbol_table module.

TDD: These tests are written first, before the implementation.
"""

import unittest
import json
import tempfile
import os


class TestSymbolTable(unittest.TestCase):
    """Tests for SymbolTable class."""

    def setUp(self):
        """Set up test fixtures."""
        from tools.symbol_table import SymbolTable

        self.symbols = SymbolTable()

    def test_create_empty_symbol_table(self):
        """Can create an empty symbol table."""
        from tools.symbol_table import SymbolTable

        st = SymbolTable()
        self.assertEqual(len(st), 0)

    def test_add_symbol(self):
        """Can add a symbol to the table."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        self.assertEqual(len(self.symbols), 1)

    def test_lookup_by_address(self):
        """Can look up a symbol by address."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        symbol = self.symbols.lookup(0xFDED)
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.name, "COUT")
        self.assertEqual(symbol.type, "routine")

    def test_lookup_nonexistent_returns_none(self):
        """Looking up nonexistent address returns None."""
        symbol = self.symbols.lookup(0x1234)
        self.assertIsNone(symbol)

    def test_lookup_by_name(self):
        """Can look up a symbol by name."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        symbol = self.symbols.lookup_name("COUT")
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.address, 0xFDED)

    def test_lookup_name_nonexistent_returns_none(self):
        """Looking up nonexistent name returns None."""
        symbol = self.symbols.lookup_name("NONEXISTENT")
        self.assertIsNone(symbol)

    def test_format_address_with_symbol(self):
        """Format address shows symbol name if known."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        formatted = self.symbols.format_address(0xFDED)
        self.assertIn("COUT", formatted)
        self.assertIn("FDED", formatted)

    def test_format_address_without_symbol(self):
        """Format address shows hex for unknown addresses."""
        formatted = self.symbols.format_address(0x1234)
        self.assertEqual(formatted, "$1234")

    def test_load_from_dict(self):
        """Can load symbols from a dictionary."""
        data = {
            "FDED": {"name": "COUT", "type": "routine", "source": "monitor"},
            "FC58": {"name": "HOME", "type": "routine", "source": "monitor"},
        }
        self.symbols.load_dict(data)
        self.assertEqual(len(self.symbols), 2)
        self.assertIsNotNone(self.symbols.lookup(0xFDED))
        self.assertIsNotNone(self.symbols.lookup(0xFC58))

    def test_export_to_dict(self):
        """Can export symbols to a dictionary."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        self.symbols.add(0xFC58, "HOME", "routine", "monitor")
        data = self.symbols.export_dict()
        self.assertIn("FDED", data)
        self.assertIn("FC58", data)
        self.assertEqual(data["FDED"]["name"], "COUT")

    def test_load_from_json_file(self):
        """Can load symbols from a JSON file."""
        data = {"version": 1, "symbols": {"FDED": {"name": "COUT", "type": "routine", "source": "monitor"}}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            self.symbols.load_file(temp_path)
            self.assertEqual(len(self.symbols), 1)
            self.assertIsNotNone(self.symbols.lookup(0xFDED))
        finally:
            os.unlink(temp_path)

    def test_save_to_json_file(self):
        """Can save symbols to a JSON file."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            self.symbols.save_file(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            self.assertIn("version", data)
            self.assertIn("symbols", data)
            self.assertIn("FDED", data["symbols"])
        finally:
            os.unlink(temp_path)

    def test_merge_symbol_tables(self):
        """Can merge two symbol tables."""
        from tools.symbol_table import SymbolTable

        other = SymbolTable()
        other.add(0xFC58, "HOME", "routine", "monitor")

        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        self.symbols.merge(other)

        self.assertEqual(len(self.symbols), 2)
        self.assertIsNotNone(self.symbols.lookup(0xFDED))
        self.assertIsNotNone(self.symbols.lookup(0xFC58))

    def test_merge_overwrites_on_conflict(self):
        """Merge overwrites existing symbols on address conflict."""
        from tools.symbol_table import SymbolTable

        other = SymbolTable()
        other.add(0xFDED, "CHAROUT", "routine", "custom")

        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        self.symbols.merge(other, overwrite=True)

        symbol = self.symbols.lookup(0xFDED)
        self.assertEqual(symbol.name, "CHAROUT")

    def test_merge_preserves_on_conflict_when_no_overwrite(self):
        """Merge preserves existing symbols when overwrite=False."""
        from tools.symbol_table import SymbolTable

        other = SymbolTable()
        other.add(0xFDED, "CHAROUT", "routine", "custom")

        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        self.symbols.merge(other, overwrite=False)

        symbol = self.symbols.lookup(0xFDED)
        self.assertEqual(symbol.name, "COUT")

    def test_filter_by_type(self):
        """Can filter symbols by type."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        self.symbols.add(0xC000, "KBD", "io", "hardware")
        self.symbols.add(0x0024, "CH", "variable", "monitor")

        routines = list(self.symbols.filter_by_type("routine"))
        self.assertEqual(len(routines), 1)
        self.assertEqual(routines[0].name, "COUT")

    def test_filter_by_source(self):
        """Can filter symbols by source."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        self.symbols.add(0xC000, "KBD", "io", "hardware")

        monitor_syms = list(self.symbols.filter_by_source("monitor"))
        self.assertEqual(len(monitor_syms), 1)
        self.assertEqual(monitor_syms[0].name, "COUT")

    def test_filter_by_address_range(self):
        """Can filter symbols by address range."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        self.symbols.add(0xFC58, "HOME", "routine", "monitor")
        self.symbols.add(0x0024, "CH", "variable", "monitor")

        rom_syms = list(self.symbols.filter_by_range(0xF000, 0xFFFF))
        self.assertEqual(len(rom_syms), 2)

    def test_iterate_all_symbols(self):
        """Can iterate over all symbols."""
        self.symbols.add(0xFDED, "COUT", "routine", "monitor")
        self.symbols.add(0xFC58, "HOME", "routine", "monitor")

        all_syms = list(self.symbols)
        self.assertEqual(len(all_syms), 2)


class TestBuiltinSymbols(unittest.TestCase):
    """Tests for built-in Apple II symbols."""

    def test_load_monitor_symbols(self):
        """Can load built-in Monitor ROM symbols."""
        from tools.symbol_table import SymbolTable

        st = SymbolTable.with_builtins()

        # Check some well-known Monitor routines
        self.assertIsNotNone(st.lookup(0xFDED))  # COUT
        self.assertIsNotNone(st.lookup(0xFC58))  # HOME
        self.assertIsNotNone(st.lookup(0xFD0C))  # RDKEY

    def test_builtin_cout_symbol(self):
        """COUT symbol is correct."""
        from tools.symbol_table import SymbolTable

        st = SymbolTable.with_builtins()

        cout = st.lookup(0xFDED)
        self.assertEqual(cout.name, "COUT")
        self.assertEqual(cout.type, "routine")

    def test_builtin_io_addresses(self):
        """I/O address symbols are included."""
        from tools.symbol_table import SymbolTable

        st = SymbolTable.with_builtins()

        kbd = st.lookup(0xC000)
        self.assertIsNotNone(kbd)
        self.assertEqual(kbd.type, "io")


class TestSymbol(unittest.TestCase):
    """Tests for Symbol dataclass."""

    def test_symbol_creation(self):
        """Can create a Symbol."""
        from tools.symbol_table import Symbol

        sym = Symbol(0xFDED, "COUT", "routine", "monitor")
        self.assertEqual(sym.address, 0xFDED)
        self.assertEqual(sym.name, "COUT")
        self.assertEqual(sym.type, "routine")
        self.assertEqual(sym.source, "monitor")

    def test_symbol_optional_comment(self):
        """Symbol can have optional comment."""
        from tools.symbol_table import Symbol

        sym = Symbol(0xFDED, "COUT", "routine", "monitor", "Character output")
        self.assertEqual(sym.comment, "Character output")

    def test_symbol_to_dict(self):
        """Symbol can be converted to dict."""
        from tools.symbol_table import Symbol

        sym = Symbol(0xFDED, "COUT", "routine", "monitor")
        d = sym.to_dict()
        self.assertEqual(d["name"], "COUT")
        self.assertEqual(d["type"], "routine")

    def test_symbol_from_dict(self):
        """Symbol can be created from dict."""
        from tools.symbol_table import Symbol

        d = {"name": "COUT", "type": "routine", "source": "monitor"}
        sym = Symbol.from_dict(0xFDED, d)
        self.assertEqual(sym.address, 0xFDED)
        self.assertEqual(sym.name, "COUT")


if __name__ == "__main__":
    unittest.main()
