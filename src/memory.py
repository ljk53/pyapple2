# Original Source: https://github.com/mnaberez/py65

from __future__ import annotations

from typing import Any, Callable, Iterable, overload


class ObservableMemory:
    def __init__(self, subject: list[int] | None = None, addrWidth: int = 16) -> None:
        self.physMask = 0xFFFF
        if addrWidth > 16:
            # even with 32-bit address space, model only 256k memory
            self.physMask = 0x3FFFF

        if subject is None:
            subject = (self.physMask + 1) * [0x00]
        self._subject = subject

        # Use regular dicts (not defaultdict) so "addr in dict" is a true
        # membership test without creating empty entries on miss.
        self._read_subscribers: dict[int, list[Callable[..., int | None]]] = {}
        self._write_subscribers: dict[int, list[Callable[..., int | None]]] = {}

        # Opt-in per-address counters for heatmap visualization.
        # When enabled, each access increments a byte counter (saturates at 255).
        self._write_counts: bytearray | None = None
        self._read_counts: bytearray | None = None

    @overload
    def __setitem__(self, address: int, value: int) -> None: ...

    @overload
    def __setitem__(self, address: slice, value: list[int]) -> None: ...

    def __setitem__(self, address: int | slice, value: int | list[int]) -> None:
        if isinstance(address, slice):
            r = range(*address.indices(self.physMask + 1))
            assert isinstance(value, list)
            for n, v in zip(r, value):
                self[n] = v
            return

        assert isinstance(value, int)
        address &= self.physMask

        callbacks = self._write_subscribers.get(address)
        if callbacks:
            for callback in callbacks:
                result = callback(address, value)
                if result is not None:
                    value = result

        self._subject[address] = value

        wc = self._write_counts
        if wc is not None:
            c = wc[address]
            if c < 255:
                wc[address] = c + 1

    @overload
    def __getitem__(self, address: int) -> int: ...

    @overload
    def __getitem__(self, address: slice) -> list[int]: ...

    def __getitem__(self, address: int | slice) -> int | list[int]:
        if isinstance(address, slice):
            r = range(*address.indices(self.physMask + 1))
            return [self[n] for n in r]

        address &= self.physMask

        callbacks = self._read_subscribers.get(address)
        if callbacks:
            final_result: int | None = None
            for callback in callbacks:
                result = callback(address)
                if result is not None:
                    final_result = result
            if final_result is not None:
                return final_result

        rc = self._read_counts
        if rc is not None:
            c = rc[address]
            if c < 255:
                rc[address] = c + 1

        return self._subject[address]

    def __getattr__(self, attribute: str) -> Any:
        return getattr(self._subject, attribute)

    def subscribe_to_write(self, address_range: Iterable[int], callback: Callable[[int, int], int | None]) -> None:
        for address in address_range:
            address &= self.physMask
            callbacks = self._write_subscribers.setdefault(address, [])
            if callback not in callbacks:
                callbacks.append(callback)

    def subscribe_to_read(self, address_range: Iterable[int], callback: Callable[[int], int | None]) -> None:
        for address in address_range:
            address &= self.physMask
            callbacks = self._read_subscribers.setdefault(address, [])
            if callback not in callbacks:
                callbacks.append(callback)

    def enable_write_tracking(self) -> None:
        """Enable per-address write counting for heatmap visualization."""
        self._write_counts = bytearray(self.physMask + 1)

    def get_write_counts(self) -> bytearray | None:
        """Return the write-count buffer, or None if tracking is disabled."""
        return self._write_counts

    def clear_write_counts(self) -> None:
        """Reset all write counts to zero."""
        if self._write_counts is not None:
            for i in range(len(self._write_counts)):
                self._write_counts[i] = 0

    def enable_read_tracking(self) -> None:
        """Enable per-address read counting for heatmap visualization."""
        self._read_counts = bytearray(self.physMask + 1)

    def get_read_counts(self) -> bytearray | None:
        """Return the read-count buffer, or None if tracking is disabled."""
        return self._read_counts

    def clear_read_counts(self) -> None:
        """Reset all read counts to zero."""
        if self._read_counts is not None:
            for i in range(len(self._read_counts)):
                self._read_counts[i] = 0

    def write(self, start_address: int, bytes: list[int]) -> None:
        start_address &= self.physMask
        self._subject[start_address : start_address + len(bytes)] = bytes
