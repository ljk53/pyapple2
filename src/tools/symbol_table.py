"""
Symbol Table for Apple II Analysis Toolkit.

Manages known and discovered symbols for the Apple II system.
Includes built-in symbols for Monitor ROM, AppleSoft BASIC, and hardware I/O.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass
class Symbol:
    """Represents a named location in the Apple II address space."""

    address: int
    name: str
    type: str  # 'routine', 'variable', 'vector', 'io', 'constant'
    source: str  # 'monitor', 'applesoft', 'hardware', 'user', 'auto'
    comment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = {
            "name": self.name,
            "type": self.type,
            "source": self.source,
        }
        if self.comment:
            d["comment"] = self.comment
        return d

    @classmethod
    def from_dict(cls, address: int, d: dict[str, Any]) -> Symbol:
        """Create Symbol from dictionary."""
        return cls(
            address=address,
            name=d["name"],
            type=d["type"],
            source=d.get("source", "unknown"),
            comment=d.get("comment"),
        )


class SymbolTable:
    """
    Manages a collection of symbols for the Apple II address space.

    Supports loading/saving from JSON files, merging tables,
    and various lookup and filtering operations.
    """

    def __init__(self) -> None:
        """Create an empty symbol table."""
        self._by_address: dict[int, Symbol] = {}
        self._by_name: dict[str, Symbol] = {}

    def __len__(self) -> int:
        """Return number of symbols in the table."""
        return len(self._by_address)

    def __iter__(self) -> Iterator[Symbol]:
        """Iterate over all symbols."""
        return iter(self._by_address.values())

    def add(self, address: int, name: str, sym_type: str, source: str, comment: str | None = None) -> Symbol:
        """Add a symbol to the table."""
        symbol = Symbol(address, name, sym_type, source, comment)
        self._by_address[address] = symbol
        self._by_name[name] = symbol
        return symbol

    def lookup(self, address: int) -> Symbol | None:
        """Look up a symbol by address."""
        return self._by_address.get(address)

    def lookup_name(self, name: str) -> Symbol | None:
        """Look up a symbol by name."""
        return self._by_name.get(name)

    def format_address(self, address: int) -> str:
        """Format an address, showing symbol name if known."""
        symbol = self.lookup(address)
        if symbol:
            return f"{symbol.name} (${address:04X})"
        return f"${address:04X}"

    def load_dict(self, data: dict[str, dict[str, Any]]) -> None:
        """Load symbols from a dictionary."""
        for addr_str, sym_data in data.items():
            address = int(addr_str, 16)
            symbol = Symbol.from_dict(address, sym_data)
            self._by_address[address] = symbol
            self._by_name[symbol.name] = symbol

    def export_dict(self) -> dict[str, dict[str, Any]]:
        """Export symbols to a dictionary."""
        return {f"{sym.address:04X}": sym.to_dict() for sym in self._by_address.values()}

    def load_file(self, path: str) -> None:
        """Load symbols from a JSON file."""
        with open(path) as f:
            data = json.load(f)

        # Handle versioned format
        if "version" in data and "symbols" in data:
            self.load_dict(data["symbols"])
        else:
            # Legacy format: just symbols
            self.load_dict(data)

    def save_file(self, path: str) -> None:
        """Save symbols to a JSON file."""
        data = {"version": 1, "symbols": self.export_dict()}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def merge(self, other: SymbolTable, overwrite: bool = True) -> None:
        """Merge another symbol table into this one."""
        for symbol in other:
            if overwrite or symbol.address not in self._by_address:
                self._by_address[symbol.address] = symbol
                self._by_name[symbol.name] = symbol

    def filter_by_type(self, sym_type: str) -> Iterator[Symbol]:
        """Filter symbols by type."""
        for symbol in self:
            if symbol.type == sym_type:
                yield symbol

    def filter_by_source(self, source: str) -> Iterator[Symbol]:
        """Filter symbols by source."""
        for symbol in self:
            if symbol.source == source:
                yield symbol

    def filter_by_range(self, start: int, end: int) -> Iterator[Symbol]:
        """Filter symbols by address range (inclusive)."""
        for symbol in self:
            if start <= symbol.address <= end:
                yield symbol

    @classmethod
    def with_builtins(cls) -> SymbolTable:
        """Create a symbol table with built-in Apple II symbols."""
        st = cls()
        st._load_builtins()
        return st

    def _load_builtins(self) -> None:
        """Load built-in Apple II symbols."""
        # Monitor ROM routines ($F800-$FFFF)
        # Verified against Monitor.ASM (Wozniak Monitor) and A2SOFT2.BIN
        monitor_routines = {
            0xF800: ("PLOT", "Plot lo-res point"),
            0xF819: ("HLINE", "Draw lo-res horizontal line"),
            0xF828: ("VLINE", "Draw lo-res vertical line"),
            0xF832: ("CLRSCR", "Clear lo-res full screen"),
            0xF836: ("CLRTOP", "Clear lo-res top screen"),
            0xF847: ("GBASCALC", "Calculate graphics base address"),
            0xF864: ("SETCOL", "Set lo-res color"),
            0xF871: ("SCRN", "Read lo-res screen color"),
            0xF882: ("INSDS1", "Print PC address"),
            0xF8D0: ("INSTDSP", "Disassemble one instruction"),
            0xF941: ("PRNTAX", "Print A and X as hex"),
            0xF948: ("PRBLNK", "Print 3 blanks"),
            0xF94A: ("PRBL2", "Print X blanks"),
            0xF953: ("PCADJ", "Adjust PC by instruction length"),
            0xFA43: ("STEP", "Disassemble one instruction"),
            0xFA62: ("RESET", "Apple II+ cold start entry"),
            0xFA86: ("IRQ", "Interrupt handler"),
            0xFAD7: ("REGDSP", "Display user registers"),
            0xFB1E: ("PREAD", "Read paddle value"),
            0xFB2F: ("INIT", "Initialize text window"),
            0xFB39: ("SETTXT", "Set text mode"),
            0xFB40: ("SETGR", "Set lo-res graphics mode"),
            0xFB4B: ("SETWND", "Set text window dimensions"),
            0xFB5B: ("TABV", "Set CV to value in A"),
            0xFBC1: ("BASCALC", "Calculate text base address"),
            0xFBD9: ("BELL1", "Handle bell character"),
            0xFBF4: ("ADVANCE", "Advance cursor right"),
            0xFBFD: ("VIDOUT", "Video output dispatch"),
            0xFC10: ("BS", "Backspace handler"),
            0xFC22: ("VTAB", "Set base address for CV"),
            0xFC42: ("CLREOP", "Clear to end of page"),
            0xFC58: ("HOME", "Clear screen and home cursor"),
            0xFC62: ("CR", "Carriage return"),
            0xFC66: ("LF", "Line feed"),
            0xFC70: ("SCROLL", "Scroll screen up one line"),
            0xFC9C: ("CLREOL", "Clear to end of line"),
            0xFCA8: ("WAIT", "Delay loop"),
            0xFCA9: ("WAIT2", "Delay loop (alt entry)"),
            0xFCB4: ("NXTA4", "Increment A4, compare to A2"),
            0xFCBA: ("NXTA1", "Increment A1, compare to A2"),
            0xFCC9: ("HEADR", "Write cassette header"),
            0xFCEC: ("RDBYTE", "Read cassette byte"),
            0xFD0C: ("RDKEY", "Read keyboard"),
            0xFD1B: ("KEYIN", "Keyboard input loop"),
            0xFD35: ("RDCHAR", "Read character with ESC"),
            0xFD67: ("GETLNZ", "Get input line with CR"),
            0xFD6A: ("GETLN", "Get input line"),
            0xFD8E: ("CROUT", "Output carriage return"),
            0xFD92: ("PRA1", "Print CR then A1 in hex"),
            0xFDA3: ("XAM8", "Examine 8 bytes of memory"),
            0xFDB3: ("XAM", "Examine memory"),
            0xFDDA: ("PRBYTE", "Print byte as 2 hex digits"),
            0xFDE3: ("PRHEX", "Print low nibble as hex"),
            0xFDE5: ("PRHEXZ", "Print hex digit with OR"),
            0xFDED: ("COUT", "Character output via vector"),
            0xFDF0: ("COUT1", "Character output direct"),
            0xFDF6: ("COUTZ", "Character output save Y"),
            0xFE18: ("SETMODE", "Set monitor mode"),
            0xFE2C: ("MOVE", "Block memory move"),
            0xFE5E: ("LIST", "Disassemble instructions"),
            0xFE80: ("SETINV", "Set inverse video mode"),
            0xFE84: ("SETNORM", "Set normal video mode"),
            0xFE89: ("SETKBD", "Set keyboard input"),
            0xFE93: ("SETVID", "Set video output"),
            0xFEB0: ("XBASIC", "Enter BASIC (cold)"),
            0xFEB3: ("BASCONT", "Continue BASIC"),
            0xFEB6: ("GO", "Execute at address"),
            0xFECA: ("USR", "Jump to user routine"),
            0xFECD: ("WRITE", "Cassette write"),
            0xFEFD: ("READ", "Cassette read"),
            0xFF2D: ("PRERR", "Print ERR"),
            0xFF3A: ("BELL", "Sound bell"),
            0xFF3F: ("RESTORE", "Restore 6502 registers"),
            0xFF4A: ("SAVE", "Save 6502 registers"),
            0xFF59: ("RESET2", "IIe reset entry"),
            0xFF65: ("MON", "Monitor command loop"),
            0xFF69: ("MONZ", "Monitor with prompt"),
            0xFFA7: ("GETNUM", "Get hex number"),
            0xFFFC: ("RESET_VEC", "Reset vector"),
        }

        for addr, (name, comment) in monitor_routines.items():
            self.add(addr, name, "routine", "monitor", comment)

        # I/O addresses ($C000-$C0FF)
        io_addresses = {
            0xC000: ("KBD", "Keyboard data"),
            0xC010: ("KBDSTRB", "Keyboard strobe"),
            0xC020: ("TAPEOUT", "Cassette output"),
            0xC030: ("SPKR", "Speaker toggle"),
            0xC050: ("TXTCLR", "Enable graphics"),
            0xC051: ("TXTSET", "Enable text"),
            0xC052: ("MIXCLR", "Full screen"),
            0xC053: ("MIXSET", "Mixed mode"),
            0xC054: ("LOWSCR", "Page 1"),
            0xC055: ("HISCR", "Page 2"),
            0xC056: ("LORES", "Lo-res mode"),
            0xC057: ("HIRES", "Hi-res mode"),
            0xC060: ("CASSETTE", "Cassette input"),
            0xC061: ("PB0", "Pushbutton 0"),
            0xC062: ("PB1", "Pushbutton 1"),
            0xC063: ("PB2", "Pushbutton 2"),
            0xC064: ("PADDL0", "Paddle 0"),
            0xC065: ("PADDL1", "Paddle 1"),
            0xC066: ("PADDL2", "Paddle 2"),
            0xC067: ("PADDL3", "Paddle 3"),
            0xC070: ("PTRIG", "Paddle trigger"),
        }

        for addr, (name, comment) in io_addresses.items():
            self.add(addr, name, "io", "hardware", comment)

        # Zero page locations
        # Verified against Monitor.ASM EQU block
        zeropage = {
            0x0020: ("WNDLFT", "Window left edge"),
            0x0021: ("WNDWDTH", "Window width"),
            0x0022: ("WNDTOP", "Window top edge"),
            0x0023: ("WNDBTM", "Window bottom"),
            0x0024: ("CH", "Cursor horizontal"),
            0x0025: ("CV", "Cursor vertical"),
            0x0026: ("GBASL", "Graphics base low"),
            0x0027: ("GBASH", "Graphics base high"),
            0x0028: ("BASL", "Text base low"),
            0x0029: ("BASH", "Text base high"),
            0x002A: ("BAS2L", "Base 2 low"),
            0x002B: ("BAS2H", "Base 2 high"),
            0x002C: ("LMNEM", "Left mnemonic"),
            0x002D: ("RMNEM", "Right mnemonic"),
            0x002E: ("FORMAT", "Format/mask byte"),
            0x0030: ("COLOR", "Lo-res color"),
            0x0031: ("MODE", "Mode byte"),
            0x0032: ("INVFLG", "Inverse flag"),
            0x0033: ("PROMPT", "Prompt character"),
            0x0036: ("CSWL", "CSW vector low"),
            0x0037: ("CSWH", "CSW vector high"),
            0x0038: ("KSWL", "KSW vector low"),
            0x0039: ("KSWH", "KSW vector high"),
            0x003C: ("A1L", "Address 1 low"),
            0x003D: ("A1H", "Address 1 high"),
            0x003E: ("A2L", "Address 2 low"),
            0x003F: ("A2H", "Address 2 high"),
            0x0040: ("A3L", "Address 3 low"),
            0x0041: ("A3H", "Address 3 high"),
            0x0042: ("A4L", "Address 4 low"),
            0x0043: ("A4H", "Address 4 high"),
            0x0044: ("A5L", "Address 5 low"),
            0x0045: ("A5H", "Address 5 high"),
            0x0048: ("STATUS", "Status byte"),
            0x0067: ("TXTPTR", "BASIC text pointer low"),
            0x0068: ("TXTPTRH", "BASIC text pointer high"),
        }

        for addr, (name, comment) in zeropage.items():
            self.add(addr, name, "variable", "monitor", comment)

        # AppleSoft BASIC entry points ($D000-$F7FF)
        # Verified against AppleSoft.ASM listing
        applesoft = {
            0xD000: ("TOKEN.ADDRESS.TABLE", "Token dispatch table"),
            0xD365: ("GTFORPNT", "Scan stack for FOR frame"),
            0xD393: ("BLTU", "Block transfer upward"),
            0xD3D6: ("CHKMEM", "Check stack memory available"),
            0xD3E3: ("REASON", "Check memory, trigger GC"),
            0xD412: ("ERROR", "Report error"),
            0xD43C: ("RESTART", "BASIC warm restart"),
            0xD52C: ("INLIN", "Input line"),
            0xD559: ("PARSE.INPUT.LINE", "Tokenize input line"),
            0xD61A: ("FNDLIN", "Find BASIC line by number"),
            0xD649: ("NEW", "Execute NEW"),
            0xD66A: ("CLEAR", "Execute CLEAR"),
            0xD6A5: ("LIST", "Execute LIST"),
            0xD766: ("FOR", "Execute FOR"),
            0xD7D2: ("NEWSTT", "Execute next statement"),
            0xD849: ("RESTORE", "Execute RESTORE"),
            0xD86E: ("STOP", "Execute STOP"),
            0xD870: ("END", "Execute END"),
            0xD896: ("CONT", "Execute CONT"),
            0xD912: ("RUN", "Execute RUN"),
            0xD921: ("GOSUB", "Execute GOSUB"),
            0xD93E: ("GOTO", "Execute GOTO"),
            0xD984: ("RETURN", "Execute RETURN"),
            0xD995: ("DATA", "Execute DATA"),
            0xD9A6: ("REMN", "REM handler"),
            0xD9C9: ("IF", "Execute IF"),
            0xD9EC: ("ONGOTO", "Execute ON GOTO/GOSUB"),
            0xDA0C: ("LINGET", "Convert line number"),
            0xDA46: ("LET", "Execute LET"),
            0xDAD5: ("PRINT", "Execute PRINT"),
            0xDAFB: ("CRDO", "Print carriage return"),
            0xDB3A: ("STROUT", "Output string at Y,A"),
            0xDB3D: ("STRPRT", "Print string descriptor"),
            0xDB57: ("OUTSP", "Print space"),
            0xDB5C: ("OUTDO", "Print character in A"),
            0xDBB2: ("INPUT", "Execute INPUT"),
            0xDBE2: ("READ", "Execute READ"),
            0xDCF9: ("NEXT", "Execute NEXT"),
            0xDD67: ("FRMNUM", "Evaluate numeric expression"),
            0xDD7B: ("FRMEVL", "Evaluate any expression"),
            0xDE60: ("FRM.ELEMENT", "Get expression element"),
            0xDEB2: ("PARCHK", "Require (expr)"),
            0xDEBE: ("CHKCOM", "Require comma"),
            0xDEC0: ("SYNCHR", "Require specific token"),
            0xDFD9: ("DIM", "Execute DIM"),
            0xDFE3: ("PTRGET", "Find/create variable"),
            0xE000: ("BASIC.COLD.VECTOR", "JMP COLD.START"),
            0xE003: ("BASIC.WARM.VECTOR", "JMP RESTART"),
            0xE10C: ("AYINT", "Convert FAC to integer"),
            0xE2F2: ("GIVAYF", "Float A,Y into FAC"),
            0xE2FF: ("POS", "Cursor position function"),
            0xE306: ("ERRDIR", "Error if direct mode"),
            0xE3C5: ("STR", "STR$ function"),
            0xE3E7: ("STRLIT", "Make string descriptor"),
            0xE597: ("CAT", "String concatenation"),
            0xE646: ("CHRSTR", "CHR$ function"),
            0xE65A: ("LEFTSTR", "LEFT$ function"),
            0xE686: ("RIGHTSTR", "RIGHT$ function"),
            0xE691: ("MIDSTR", "MID$ function"),
            0xE6D6: ("LEN", "LEN function"),
            0xE6E5: ("ASC", "ASC function"),
            0xE6F5: ("GTBYTC", "Scan and get byte in X"),
            0xE6F8: ("GETBYT", "Get byte value in X"),
            0xE6FB: ("CONINT", "Convert FAC to byte in X"),
            0xE707: ("VAL", "VAL function"),
            0xE752: ("GETADR", "Convert FAC to address"),
            0xE764: ("PEEK", "PEEK function"),
            0xE77B: ("POKE", "Execute POKE"),
            0xE784: ("WAIT", "Execute WAIT"),
            0xE7A7: ("FSUB", "Floating subtract"),
            0xE7BE: ("FADD", "Floating add"),
            0xE941: ("LOG", "LOG function"),
            0xE97F: ("FMULT", "Floating multiply"),
            0xEA66: ("FDIV", "Floating divide"),
            0xEAF9: ("LOAD.FAC.FROM.YA", "Unpack to FAC"),
            0xEB2B: ("STORE.FAC.AT.YX.ROUNDED", "Pack FAC to memory"),
            0xEB82: ("SIGN", "Sign of FAC"),
            0xEBAF: ("ABS", "ABS function"),
            0xEBB2: ("FCOMP", "Compare with FAC"),
            0xEC23: ("INT", "INT function"),
            0xEC4A: ("FIN", "ASCII to FAC"),
            0xED24: ("LINPRT", "Print integer"),
            0xED34: ("FOUT", "FAC to ASCII"),
            0xEE8D: ("SQR", "SQR function"),
            0xEE97: ("FPWRT", "Exponentiation"),
            0xEF09: ("EXP", "EXP function"),
            0xEFF1: ("SIN", "SIN function"),
            0xEFEA: ("COS", "COS function"),
            0xF03A: ("TAN", "TAN function"),
            0xF09E: ("ATN", "ATN function"),
            0xF128: ("COLD.START", "Cold start initialization"),
            0xF1D5: ("CALL", "Execute CALL"),
            0xF2CB: ("ONERR", "ON ERR GOTO setup"),
            0xF318: ("RESUME", "Execute RESUME"),
        }

        for addr, (name, comment) in applesoft.items():
            self.add(addr, name, "routine", "applesoft", comment)


# Standalone CLI support
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Apple II Symbol Table Manager")
    parser.add_argument("--list", action="store_true", help="List built-in symbols")
    parser.add_argument("--export", metavar="FILE", help="Export symbols to JSON file")
    parser.add_argument("--merge", metavar="FILE", help="Merge symbols from JSON file")
    parser.add_argument("--type", metavar="TYPE", help="Filter by type")
    parser.add_argument("--source", metavar="SOURCE", help="Filter by source")
    parser.add_argument("--range", metavar="START-END", help="Filter by address range")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    args = parser.parse_args()

    st = SymbolTable.with_builtins()

    if args.merge:
        other = SymbolTable()
        other.load_file(args.merge)
        st.merge(other)

    # Apply filters
    symbols = list(st)

    if args.type:
        symbols = [s for s in symbols if s.type == args.type]

    if args.source:
        symbols = [s for s in symbols if s.source == args.source]

    if args.range:
        start, end = args.range.split("-")
        start = int(start, 16)
        end = int(end, 16)
        symbols = [s for s in symbols if start <= s.address <= end]

    # Sort by address
    symbols.sort(key=lambda s: s.address)

    if args.export:
        st.save_file(args.export)
        print(f"Exported {len(st)} symbols to {args.export}")
    elif args.list or not any([args.export]):
        if args.format == "json":
            import json as json_mod  # noqa: F811

            print(json_mod.dumps([s.to_dict() | {"address": f"${s.address:04X}"} for s in symbols], indent=2))
        else:
            print(f"{'Address':<8} {'Name':<16} {'Type':<10} {'Source':<12} Comment")
            print("-" * 70)
            for s in symbols:
                comment = s.comment or ""
                print(f"${s.address:04X}    {s.name:<16} {s.type:<10} {s.source:<12} {comment}")
            print(f"\nTotal: {len(symbols)} symbols")
