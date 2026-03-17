# Original Source: https://github.com/jtauber/applepy

from __future__ import annotations

from typing import Any, Callable


def signed(x: int) -> int:
    if x > 0x7F:
        x = x - 0x100
    return x


class Disassemble:
    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self.setup_ops()

    def setup_ops(self) -> None:
        self.ops: list[tuple[int, str] | tuple[int, str, Callable[[int], dict[str, Any]]]] = [(1, "???")] * 0x100
        self.ops[0x00] = (
            1,
            "BRK",
        )
        self.ops[0x01] = (2, "ORA", self.indirect_x_mode)
        self.ops[0x05] = (2, "ORA", self.zero_page_mode)
        self.ops[0x06] = (2, "ASL", self.zero_page_mode)
        self.ops[0x08] = (
            1,
            "PHP",
        )
        self.ops[0x09] = (2, "ORA", self.immediate_mode)
        self.ops[0x0A] = (
            1,
            "ASL",
        )
        self.ops[0x0D] = (3, "ORA", self.absolute_mode)
        self.ops[0x0E] = (3, "ASL", self.absolute_mode)
        self.ops[0x10] = (2, "BPL", self.relative_mode)
        self.ops[0x11] = (2, "ORA", self.indirect_y_mode)
        self.ops[0x15] = (2, "ORA", self.zero_page_x_mode)
        self.ops[0x16] = (2, "ASL", self.zero_page_x_mode)
        self.ops[0x18] = (
            1,
            "CLC",
        )
        self.ops[0x19] = (3, "ORA", self.absolute_y_mode)
        self.ops[0x1D] = (3, "ORA", self.absolute_x_mode)
        self.ops[0x1E] = (3, "ASL", self.absolute_x_mode)
        self.ops[0x20] = (3, "JSR", self.absolute_mode)
        self.ops[0x21] = (2, "AND", self.indirect_x_mode)
        self.ops[0x24] = (2, "BIT", self.zero_page_mode)
        self.ops[0x25] = (2, "AND", self.zero_page_mode)
        self.ops[0x26] = (2, "ROL", self.zero_page_mode)
        self.ops[0x28] = (
            1,
            "PLP",
        )
        self.ops[0x29] = (2, "AND", self.immediate_mode)
        self.ops[0x2A] = (
            1,
            "ROL",
        )
        self.ops[0x2C] = (3, "BIT", self.absolute_mode)
        self.ops[0x2D] = (3, "AND", self.absolute_mode)
        self.ops[0x2E] = (3, "ROL", self.absolute_mode)
        self.ops[0x30] = (2, "BMI", self.relative_mode)
        self.ops[0x31] = (2, "AND", self.indirect_y_mode)
        self.ops[0x35] = (2, "AND", self.zero_page_x_mode)
        self.ops[0x36] = (2, "ROL", self.zero_page_x_mode)
        self.ops[0x38] = (
            1,
            "SEC",
        )
        self.ops[0x39] = (3, "AND", self.absolute_y_mode)
        self.ops[0x3D] = (3, "AND", self.absolute_x_mode)
        self.ops[0x3E] = (3, "ROL", self.absolute_x_mode)
        self.ops[0x40] = (
            1,
            "RTI",
        )
        self.ops[0x41] = (2, "EOR", self.indirect_x_mode)
        self.ops[0x45] = (2, "EOR", self.zero_page_mode)
        self.ops[0x46] = (2, "LSR", self.zero_page_mode)
        self.ops[0x48] = (
            1,
            "PHA",
        )
        self.ops[0x49] = (2, "EOR", self.immediate_mode)
        self.ops[0x4A] = (
            1,
            "LSR",
        )
        self.ops[0x4C] = (3, "JMP", self.absolute_mode)
        self.ops[0x4D] = (3, "EOR", self.absolute_mode)
        self.ops[0x4E] = (3, "LSR", self.absolute_mode)
        self.ops[0x50] = (2, "BVC", self.relative_mode)
        self.ops[0x51] = (2, "EOR", self.indirect_y_mode)
        self.ops[0x55] = (2, "EOR", self.zero_page_x_mode)
        self.ops[0x56] = (2, "LSR", self.zero_page_x_mode)
        self.ops[0x58] = (
            1,
            "CLI",
        )
        self.ops[0x59] = (3, "EOR", self.absolute_y_mode)
        self.ops[0x5D] = (3, "EOR", self.absolute_x_mode)
        self.ops[0x5E] = (3, "LSR", self.absolute_x_mode)
        self.ops[0x60] = (
            1,
            "RTS",
        )
        self.ops[0x61] = (2, "ADC", self.indirect_x_mode)
        self.ops[0x65] = (2, "ADC", self.zero_page_mode)
        self.ops[0x66] = (2, "ROR", self.zero_page_mode)
        self.ops[0x68] = (
            1,
            "PLA",
        )
        self.ops[0x69] = (2, "ADC", self.immediate_mode)
        self.ops[0x6A] = (
            1,
            "ROR",
        )
        self.ops[0x6C] = (3, "JMP", self.indirect_mode)
        self.ops[0x6D] = (3, "ADC", self.absolute_mode)
        self.ops[0x6E] = (3, "ROR", self.absolute_mode)
        self.ops[0x70] = (2, "BVS", self.relative_mode)
        self.ops[0x71] = (2, "ADC", self.indirect_y_mode)
        self.ops[0x75] = (2, "ADC", self.zero_page_x_mode)
        self.ops[0x76] = (2, "ROR", self.zero_page_x_mode)
        self.ops[0x78] = (
            1,
            "SEI",
        )
        self.ops[0x79] = (3, "ADC", self.absolute_y_mode)
        self.ops[0x7D] = (3, "ADC", self.absolute_x_mode)
        self.ops[0x7E] = (3, "ROR", self.absolute_x_mode)
        self.ops[0x81] = (2, "STA", self.indirect_x_mode)
        self.ops[0x84] = (2, "STY", self.zero_page_mode)
        self.ops[0x85] = (2, "STA", self.zero_page_mode)
        self.ops[0x86] = (2, "STX", self.zero_page_mode)
        self.ops[0x88] = (
            1,
            "DEY",
        )
        self.ops[0x8A] = (
            1,
            "TXA",
        )
        self.ops[0x8C] = (3, "STY", self.absolute_mode)
        self.ops[0x8D] = (3, "STA", self.absolute_mode)
        self.ops[0x8E] = (3, "STX", self.absolute_mode)
        self.ops[0x90] = (2, "BCC", self.relative_mode)
        self.ops[0x91] = (2, "STA", self.indirect_y_mode)
        self.ops[0x94] = (2, "STY", self.zero_page_x_mode)
        self.ops[0x95] = (2, "STA", self.zero_page_x_mode)
        self.ops[0x96] = (2, "STX", self.zero_page_y_mode)
        self.ops[0x98] = (
            1,
            "TYA",
        )
        self.ops[0x99] = (3, "STA", self.absolute_y_mode)
        self.ops[0x9A] = (
            1,
            "TXS",
        )
        self.ops[0x9D] = (3, "STA", self.absolute_x_mode)
        self.ops[0xA0] = (2, "LDY", self.immediate_mode)
        self.ops[0xA1] = (2, "LDA", self.indirect_x_mode)
        self.ops[0xA2] = (2, "LDX", self.immediate_mode)
        self.ops[0xA4] = (2, "LDY", self.zero_page_mode)
        self.ops[0xA5] = (2, "LDA", self.zero_page_mode)
        self.ops[0xA6] = (2, "LDX", self.zero_page_mode)
        self.ops[0xA8] = (
            1,
            "TAY",
        )
        self.ops[0xA9] = (2, "LDA", self.immediate_mode)
        self.ops[0xAA] = (
            1,
            "TAX",
        )
        self.ops[0xAC] = (3, "LDY", self.absolute_mode)
        self.ops[0xAD] = (3, "LDA", self.absolute_mode)
        self.ops[0xAE] = (3, "LDX", self.absolute_mode)
        self.ops[0xB0] = (2, "BCS", self.relative_mode)
        self.ops[0xB1] = (2, "LDA", self.indirect_y_mode)
        self.ops[0xB4] = (2, "LDY", self.zero_page_x_mode)
        self.ops[0xB5] = (2, "LDA", self.zero_page_x_mode)
        self.ops[0xB6] = (2, "LDX", self.zero_page_y_mode)
        self.ops[0xB8] = (
            1,
            "CLV",
        )
        self.ops[0xB9] = (3, "LDA", self.absolute_y_mode)
        self.ops[0xBA] = (
            1,
            "TSX",
        )
        self.ops[0xBC] = (3, "LDY", self.absolute_x_mode)
        self.ops[0xBD] = (3, "LDA", self.absolute_x_mode)
        self.ops[0xBE] = (3, "LDX", self.absolute_y_mode)
        self.ops[0xC0] = (2, "CPY", self.immediate_mode)
        self.ops[0xC1] = (2, "CMP", self.indirect_x_mode)
        self.ops[0xC4] = (2, "CPY", self.zero_page_mode)
        self.ops[0xC5] = (2, "CMP", self.zero_page_mode)
        self.ops[0xC6] = (2, "DEC", self.zero_page_mode)
        self.ops[0xC8] = (
            1,
            "INY",
        )
        self.ops[0xC9] = (2, "CMP", self.immediate_mode)
        self.ops[0xCA] = (
            1,
            "DEX",
        )
        self.ops[0xCC] = (3, "CPY", self.absolute_mode)
        self.ops[0xCD] = (3, "CMP", self.absolute_mode)
        self.ops[0xCE] = (3, "DEC", self.absolute_mode)
        self.ops[0xD0] = (2, "BNE", self.relative_mode)
        self.ops[0xD1] = (2, "CMP", self.indirect_y_mode)
        self.ops[0xD5] = (2, "CMP", self.zero_page_x_mode)
        self.ops[0xD6] = (2, "DEC", self.zero_page_x_mode)
        self.ops[0xD8] = (
            1,
            "CLD",
        )
        self.ops[0xD9] = (3, "CMP", self.absolute_y_mode)
        self.ops[0xDD] = (3, "CMP", self.absolute_x_mode)
        self.ops[0xDE] = (3, "DEC", self.absolute_x_mode)
        self.ops[0xE0] = (2, "CPX", self.immediate_mode)
        self.ops[0xE1] = (2, "SBC", self.indirect_x_mode)
        self.ops[0xE4] = (2, "CPX", self.zero_page_mode)
        self.ops[0xE5] = (2, "SBC", self.zero_page_mode)
        self.ops[0xE6] = (2, "INC", self.zero_page_mode)
        self.ops[0xE8] = (
            1,
            "INX",
        )
        self.ops[0xE9] = (2, "SBC", self.immediate_mode)
        self.ops[0xEA] = (
            1,
            "NOP",
        )
        self.ops[0xEC] = (3, "CPX", self.absolute_mode)
        self.ops[0xED] = (3, "SBC", self.absolute_mode)
        self.ops[0xEE] = (3, "INC", self.absolute_mode)
        self.ops[0xF0] = (2, "BEQ", self.relative_mode)
        self.ops[0xF1] = (2, "SBC", self.indirect_y_mode)
        self.ops[0xF5] = (2, "SBC", self.zero_page_x_mode)
        self.ops[0xF6] = (2, "INC", self.zero_page_x_mode)
        self.ops[0xF8] = (
            1,
            "SED",
        )
        self.ops[0xF9] = (3, "SBC", self.absolute_y_mode)
        self.ops[0xFD] = (3, "SBC", self.absolute_x_mode)
        self.ops[0xFE] = (3, "INC", self.absolute_x_mode)

    def absolute_mode(self, pc: int) -> dict[str, Any]:
        a = self.runtime.read_word(pc + 1)
        return {
            "operand": "$%04X" % a,
            "memory": [a, 2, self.runtime.read_word(a)],
        }

    def absolute_x_mode(self, pc: int) -> dict[str, Any]:
        a = self.runtime.read_word(pc + 1)
        e = a + self.runtime.x_index
        return {
            "operand": "$%04X,X" % a,
            "memory": [e, 1, self.runtime.read_byte(e)],
        }

    def absolute_y_mode(self, pc: int) -> dict[str, Any]:
        a = self.runtime.read_word(pc + 1)
        e = a + self.runtime.y_index
        return {
            "operand": "$%04X,Y" % a,
            "memory": [e, 1, self.runtime.read_byte(e)],
        }

    def immediate_mode(self, pc: int) -> dict[str, Any]:
        return {
            "operand": "#$%02X" % (self.runtime.read_byte(pc + 1)),
        }

    def indirect_mode(self, pc: int) -> dict[str, Any]:
        a = self.runtime.read_word(pc + 1)
        return {
            "operand": "($%04X)" % a,
            "memory": [a, 2, self.runtime.read_word(a)],
        }

    def indirect_x_mode(self, pc: int) -> dict[str, Any]:
        z = self.runtime.read_byte(pc + 1)
        a = self.runtime.read_word((z + self.runtime.x_index) % 0x100)
        return {
            "operand": "($%02X,X)" % z,
            "memory": [a, 1, self.runtime.read_byte(a)],
        }

    def indirect_y_mode(self, pc: int) -> dict[str, Any]:
        z = self.runtime.read_byte(pc + 1)
        a = self.runtime.read_word(z) + self.runtime.y_index
        return {
            "operand": "($%02X),Y" % z,
            "memory": [a, 1, self.runtime.read_byte(a)],
        }

    def relative_mode(self, pc: int) -> dict[str, Any]:
        return {
            "operand": "$%04X" % (pc + signed(self.runtime.read_byte(pc + 1) + 2)),
        }

    def zero_page_mode(self, pc: int) -> dict[str, Any]:
        a = self.runtime.read_byte(pc + 1)
        return {
            "operand": "$%02X" % a,
            "memory": [a, 1, self.runtime.read_byte(a)],
        }

    def zero_page_x_mode(self, pc: int) -> dict[str, Any]:
        z = self.runtime.read_byte(pc + 1)
        a = (z + self.runtime.x_index) % 0x100
        return {
            "operand": "$%02X,X" % z,
            "memory": [a, 1, self.runtime.read_byte(a)],
        }

    def zero_page_y_mode(self, pc: int) -> dict[str, Any]:
        z = self.runtime.read_byte(pc + 1)
        a = (z + self.runtime.y_index) % 0x100
        return {
            "operand": "$%02X,Y" % z,
            "memory": [a, 1, self.runtime.read_byte(a)],
        }

    def disasm(self, pc: int) -> tuple[dict[str, Any], int]:
        op = self.runtime.read_byte(pc)
        info = self.ops[op]
        r = {
            "address": pc,
            "bytes": [self.runtime.read_byte(pc + i) for i in range(info[0])],
            "mnemonic": info[1],
        }
        if len(info) > 2:
            r.update(info[2](pc))
        return r, info[0]
