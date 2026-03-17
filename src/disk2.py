"""
Apple II Disk II floppy disk controller emulation (L1).

Emulates the P5A Disk II controller card:
- Stepper motor phase control (track seeking)
- Nibble-level data stream from .dsk/.po disk images
- 6-and-2 encoding for sector data
- 4-and-4 encoding for address fields
- Write support: captures nibbles, denibblizes, updates disk image

Mounts on ObservableMemory bus at $C080+slot*16 (default slot 6 = $C0E0).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory import ObservableMemory

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Sector interleave tables  (physical position → DOS/ProDOS logical sector)
# ---------------------------------------------------------------------------
# Ref: AppleIIGo DiskII.java — gcrLogicalDos33Sector / gcrLogicalProdosSector

# DOS 3.3: physical position → file sector in a .dsk image.
_DOS33_SECTOR = [0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15]

# ProDOS: physical position → file sector in a .po image.
_PRODOS_SECTOR = [0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]


def _detect_prodos_order(disk_data: bytes | bytearray) -> bool:
    """Auto-detect whether a .dsk image uses ProDOS sector ordering.

    Follows the VTOC catalog chain (T17/S0) under both DOS 3.3 and
    ProDOS sector orderings.  Returns True if the ProDOS ordering
    produces a valid chain and the DOS ordering does not.
    """
    if len(disk_data) < 35 * 16 * 256:
        return False

    def _catalog_chain_length(table: list[int]) -> int:
        """Follow catalog chain, return length (-1 if invalid)."""
        vtoc_off = 17 * 4096 + table[0] * 256
        t, s = disk_data[vtoc_off + 1], disk_data[vtoc_off + 2]
        length = 0
        seen: set[tuple[int, int]] = set()
        while (t, s) != (0, 0):
            if t > 34 or s > 15 or (t, s) in seen:
                return -1
            seen.add((t, s))
            off = t * 4096 + table[s] * 256
            t, s = disk_data[off + 1], disk_data[off + 2]
            length += 1
            if length > 50:
                return -1
        return length

    dos_len = _catalog_chain_length(list(range(16)))  # identity = DOS order
    po_len = _catalog_chain_length(_PRODOS_SECTOR)
    # Prefer the ordering that yields a longer valid chain
    if po_len > dos_len:
        return True
    return False


# ---------------------------------------------------------------------------
# 6-and-2 write translate table (6-bit value -> valid disk nibble)
# ---------------------------------------------------------------------------

_WRITE_TABLE = [
    0x96,
    0x97,
    0x9A,
    0x9B,
    0x9D,
    0x9E,
    0x9F,
    0xA6,
    0xA7,
    0xAB,
    0xAC,
    0xAD,
    0xAE,
    0xAF,
    0xB2,
    0xB3,
    0xB4,
    0xB5,
    0xB6,
    0xB7,
    0xB9,
    0xBA,
    0xBB,
    0xBC,
    0xBD,
    0xBE,
    0xBF,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
    0xD3,
    0xD6,
    0xD7,
    0xD9,
    0xDA,
    0xDB,
    0xDC,
    0xDD,
    0xDE,
    0xDF,
    0xE5,
    0xE6,
    0xE7,
    0xE9,
    0xEA,
    0xEB,
    0xEC,
    0xED,
    0xEE,
    0xEF,
    0xF2,
    0xF3,
    0xF4,
    0xF5,
    0xF6,
    0xF7,
    0xF9,
    0xFA,
    0xFB,
    0xFC,
    0xFD,
    0xFE,
    0xFF,
]

# Reverse lookup: disk nibble → 6-bit value
_READ_TABLE: list[int] = [0] * 256
for _i, _v in enumerate(_WRITE_TABLE):
    _READ_TABLE[_v] = _i


# ---------------------------------------------------------------------------
# Encoding / decoding helpers
# ---------------------------------------------------------------------------


def _encode_44(val: int) -> list[int]:
    """4-and-4 encode a byte into two disk bytes."""
    return [(val >> 1) | 0xAA, val | 0xAA]


def _decode_44(b1: int, b2: int) -> int:
    """4-and-4 decode two disk bytes into one data byte."""
    return ((b1 & 0x55) << 1) | (b2 & 0x55)


def _encode_62(data: bytes | list[int]) -> list[int]:
    """6-and-2 encode 256 data bytes into 343 disk nibbles."""
    # Pack bottom 2 bits (bit-swapped) into 86 auxiliary values.
    # The P5A boot ROM / RWTS denibblize loop reads aux in reverse:
    # data[Y] uses aux[85 - (Y % 86)], so we pack accordingly.
    aux = [0] * 86
    for i in range(256):
        low2 = ((data[i] & 1) << 1) | ((data[i] & 2) >> 1)
        aux[85 - (i % 86)] |= (low2 & 3) << ((i // 86) * 2)

    # Build raw 6-bit value sequence:
    # aux bytes in REVERSE order, then data top-6-bits in forward order
    raw = []
    for i in range(85, -1, -1):
        raw.append(aux[i] & 0x3F)
    for i in range(256):
        raw.append(data[i] >> 2)

    # XOR encode and translate to disk nibbles
    result = []
    prev = 0
    for val in raw:
        result.append(_WRITE_TABLE[val ^ prev])
        prev = val
    result.append(_WRITE_TABLE[prev])  # checksum
    return result  # 343 bytes


def _decode_62(nibbles: list[int]) -> bytes | None:
    """6-and-2 decode 343 disk nibbles into 256 data bytes.

    Returns None if checksum fails.
    """
    if len(nibbles) < 343:
        return None

    # Reverse translate nibbles → 6-bit values, then XOR decode
    raw = []
    prev = 0
    for i in range(342):
        val = _READ_TABLE[nibbles[i]] ^ prev
        raw.append(val)
        prev = val
    # Checksum: last nibble should decode to 0 when XORed with prev
    if _READ_TABLE[nibbles[342]] ^ prev != 0:
        return None

    # raw[0..85] = aux (in reverse order), raw[86..341] = data top 6 bits
    aux = raw[:86]
    data = bytearray(256)
    for i in range(256):
        top6 = raw[86 + i] << 2
        # aux is stored in reverse: aux[85-i%86] has bits for data[i]
        a = aux[85 - (i % 86)]
        shift = (i // 86) * 2
        low2_swapped = (a >> shift) & 3
        low2 = ((low2_swapped & 1) << 1) | ((low2_swapped & 2) >> 1)
        data[i] = (top6 | low2) & 0xFF

    return bytes(data)


def _nibblize_sector(volume: int, track: int, phys_sector: int, data: bytes | list[int]) -> list[int]:
    """Convert one 256-byte sector to a nibble byte sequence."""
    nibbles: list[int] = []

    # Gap 1 (self-sync)
    nibbles.extend([0xFF] * 16)

    # Address field
    nibbles.extend([0xD5, 0xAA, 0x96])  # prologue
    nibbles.extend(_encode_44(volume))
    nibbles.extend(_encode_44(track))
    nibbles.extend(_encode_44(phys_sector))
    nibbles.extend(_encode_44(volume ^ track ^ phys_sector))
    nibbles.extend([0xDE, 0xAA, 0xEB])  # epilogue

    # Gap 2
    nibbles.extend([0xFF] * 8)

    # Data field
    nibbles.extend([0xD5, 0xAA, 0xAD])  # prologue
    nibbles.extend(_encode_62(data))
    nibbles.extend([0xDE, 0xAA, 0xEB])  # epilogue

    return nibbles


# ---------------------------------------------------------------------------
# Disk II Controller
# ---------------------------------------------------------------------------


class Disk2Controller:
    """Apple II Disk II floppy disk controller.

    Mounts on the ObservableMemory bus.  Handles:
    - Phase stepping (track seek)
    - Motor on/off, drive select
    - Q6/Q7 mode latches
    - Nibble stream reads from $C08C,X
    - Nibble stream writes (sector capture + denibblize + image update)

    Also loads the P5A boot ROM into slot ROM space ($Cn00).
    """

    def __init__(self, mem: ObservableMemory, slot: int = 6) -> None:
        self.mem = mem
        self.slot = slot
        self.io_base = 0xC080 + slot * 16
        self.rom_base = 0xC000 + slot * 256

        # Controller state
        self.motor_on = False
        self.drive = 0  # 0 or 1
        self.q6 = False
        self.q7 = False
        self.phases = [False] * 4
        self.half_track = 0  # 0-69

        # Disk images: (mutable bytearray, is_po) per drive
        self.disks: list[tuple[bytearray, bool] | None] = [None, None]

        # Nibblized track cache
        self._track_cache: dict[tuple[int, int], list[int]] = {}
        self._nibble_pos = 0

        # Write state
        self._write_latch = 0
        self._write_buf: list[int] = []
        self._last_addr_track = -1
        self._last_addr_sector = -1

        # Address field detection state machine (runs during reads)
        self._addr_state = 0  # 0:idle 1:D5 2:D5AA 3:reading_fields
        self._addr_buf: list[int] = []

        # Mount I/O handlers
        for i in range(16):
            addr = self.io_base + i
            mem.subscribe_to_read([addr], self._io_read)
            mem.subscribe_to_write([addr], self._io_write)

    # -- Factory --

    @classmethod
    def attach(
        cls, mem: ObservableMemory, disk_path: str, disk2_path: str | None = None, slot: int = 6
    ) -> Disk2Controller:
        """Create controller, load P5A ROM, insert disk image(s).

        Locates FLOPPY.ROM relative to project root, strips 4-byte header
        if present, auto-detects .po vs .dsk from extension.
        """
        ctrl = cls(mem, slot)

        # Load Disk II boot ROM (P5A)
        floppy_rom_path = os.path.join(_PROJECT_ROOT, "bin", "FLOPPY.ROM")
        with open(floppy_rom_path, "rb") as f:
            rom_data = f.read()
        if len(rom_data) > 256:
            rom_data = rom_data[4:]  # strip 4-byte header
        ctrl.load_rom(rom_data)

        # Insert drive 0
        is_po = disk_path.lower().endswith(".po")
        with open(disk_path, "rb") as f:
            disk_data = f.read()
        ctrl.insert_disk(0, disk_data, is_po=is_po)

        # Insert drive 1 if specified
        if disk2_path:
            is_po2 = disk2_path.lower().endswith(".po")
            with open(disk2_path, "rb") as f:
                disk2_data = f.read()
            ctrl.insert_disk(1, disk2_data, is_po=is_po2)

        return ctrl

    # -- Public API --

    def load_rom(self, rom_data: bytes) -> None:
        """Load the Disk II boot ROM into slot ROM space."""
        for i, b in enumerate(rom_data):
            self.mem._subject[self.rom_base + i] = b

    def insert_disk(self, drive: int, disk_data: bytes | bytearray, is_po: bool = False) -> None:
        """Insert a disk image into a drive (0 or 1).

        For .dsk files, auto-detects whether the image uses DOS 3.3
        or ProDOS sector ordering by following the VTOC catalog chain
        under both interpretations.
        """
        if not is_po:
            is_po = _detect_prodos_order(disk_data)
        self.disks[drive] = (bytearray(disk_data), is_po)
        self._track_cache.clear()

    def save_disk(self, drive: int, path: str) -> None:
        """Write the in-memory disk image to a file."""
        disk = self.disks[drive]
        if disk is not None:
            with open(path, "wb") as f:
                f.write(disk[0])

    # -- I/O handlers --

    def _io_read(self, addr: int) -> int | None:
        offset = addr - self.io_base
        self._handle_switch(offset)
        if offset == 0x0C:  # Q6L
            if not self.q7:
                # Read mode: return next nibble
                return self._read_nibble()
            else:
                # Write mode: shift out the write latch byte
                self._write_shift()
                return self._write_latch
        elif offset == 0x0D:  # Q6H
            if not self.q7:
                # Sense write protect: bit 7 = 0 means NOT protected
                return 0x00
            else:
                # Load write latch (read returns latch value)
                return self._write_latch
        return None

    def _io_write(self, addr: int, val: int) -> None:
        offset = addr - self.io_base
        if offset == 0x0D and self.q7:
            # Q6H + Q7H: load write latch with data byte
            self._write_latch = val
        self._handle_switch(offset)

    # -- Switch handling --

    def _handle_switch(self, offset: int) -> None:
        if offset < 8:
            phase = offset >> 1
            on = bool(offset & 1)
            old = self.phases[phase]
            self.phases[phase] = on
            if on and not old:
                self._step_head(phase)
        elif offset == 0x08:
            self.motor_on = False
        elif offset == 0x09:
            self.motor_on = True
        elif offset == 0x0A:
            self.drive = 0
        elif offset == 0x0B:
            self.drive = 1
        elif offset == 0x0C:
            self.q6 = False
        elif offset == 0x0D:
            self.q6 = True
        elif offset == 0x0E:
            if self.q7:
                # Leaving write mode → flush any buffered write
                self._flush_write()
            self.q7 = False
        elif offset == 0x0F:
            if not self.q7:
                # Entering write mode → reset write buffer
                self._write_buf.clear()
            self.q7 = True

    # -- Head stepping --

    def _step_head(self, phase: int) -> None:
        """Move the head one half-track based on phase vs current position."""
        current_phase = self.half_track & 3
        if current_phase == (phase + 1) % 4:
            if self.half_track > 0:
                self.half_track -= 1
        elif current_phase == (phase + 3) % 4:
            if self.half_track < 69:
                self.half_track += 1

    # -- Nibble read stream --

    def _read_nibble(self) -> int:
        track = self.half_track >> 1
        key = (self.drive, track)
        if key not in self._track_cache:
            self._track_cache[key] = self._nibblize_track(track)

        nibbles = self._track_cache[key]
        if not nibbles:
            return 0x00

        byte = nibbles[self._nibble_pos % len(nibbles)]
        self._nibble_pos = (self._nibble_pos + 1) % len(nibbles)

        # State machine: detect address field D5 AA 96 as it streams by
        self._track_address_byte(byte)

        return byte

    def _track_address_byte(self, byte: int) -> None:
        """Track address field bytes using a state machine."""
        if self._addr_state == 0:
            if byte == 0xD5:
                self._addr_state = 1
        elif self._addr_state == 1:
            if byte == 0xAA:
                self._addr_state = 2
            else:
                self._addr_state = 1 if byte == 0xD5 else 0
        elif self._addr_state == 2:
            if byte == 0x96:
                self._addr_state = 3
                self._addr_buf = []
            else:
                self._addr_state = 1 if byte == 0xD5 else 0
        elif self._addr_state == 3:
            self._addr_buf.append(byte)
            if len(self._addr_buf) == 8:
                # vol(2), track(2), sector(2), checksum(2)
                self._last_addr_track = _decode_44(self._addr_buf[2], self._addr_buf[3])
                self._last_addr_sector = _decode_44(self._addr_buf[4], self._addr_buf[5])
                self._addr_state = 0

    # -- Write support --

    def _write_shift(self) -> None:
        """Accept the current write latch byte into the write buffer."""
        self._write_buf.append(self._write_latch)

    def _flush_write(self) -> None:
        """Process the write buffer when leaving write mode.

        Searches for data field prologue (D5 AA AD) in the write buffer,
        extracts the 343 nibbles, decodes, and writes to the disk image.
        """
        buf = self._write_buf
        if len(buf) < 346:  # prologue(3) + data(343)
            return

        # Find data field prologue D5 AA AD
        for i in range(len(buf) - 345):
            if buf[i] == 0xD5 and buf[i + 1] == 0xAA and buf[i + 2] == 0xAD:
                data_nibbles = buf[i + 3 : i + 3 + 343]
                decoded = _decode_62(data_nibbles)
                if decoded is not None:
                    self._write_sector(decoded)
                break

        self._write_buf.clear()

    def _write_sector(self, data: bytes) -> None:
        """Write 256 decoded bytes to the disk image at the last-seen sector."""
        disk = self.disks[self.drive]
        if disk is None:
            return
        disk_data, is_po = disk
        track = self._last_addr_track
        phys_sector = self._last_addr_sector
        table = _PRODOS_SECTOR if is_po else _DOS33_SECTOR
        file_sector = table[phys_sector] if phys_sector < 16 else phys_sector
        offset = (track * 16 + file_sector) * 256
        if offset + 256 <= len(disk_data):
            disk_data[offset : offset + 256] = data
            # Invalidate track cache so re-reads see the new data
            key = (self.drive, track)
            if key in self._track_cache:
                del self._track_cache[key]

    # -- Track nibblization --

    def _nibblize_track(self, track: int) -> list[int]:
        disk = self.disks[self.drive]
        if disk is None:
            return [0xFF] * 100

        disk_data, is_po = disk
        volume = 254
        nibbles: list[int] = []

        for phys in range(16):
            sector_data = self._get_sector_data(disk_data, track, phys, is_po)
            nibbles.extend(_nibblize_sector(volume, track, phys, sector_data))

        # End-of-track gap
        nibbles.extend([0xFF] * 64)
        return nibbles

    @staticmethod
    def _get_sector_data(disk_data: bytes | bytearray, track: int, phys_sector: int, is_po: bool) -> bytes:
        """Read 256 bytes for a physical sector from the disk image."""
        file_sector = _PRODOS_SECTOR[phys_sector] if is_po else _DOS33_SECTOR[phys_sector]
        offset = (track * 16 + file_sector) * 256
        if offset + 256 > len(disk_data):
            return bytes(256)
        return bytes(disk_data[offset : offset + 256])
