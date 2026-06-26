"""
Opaque passthrough record for unrecognized PCB primitives.

PcbLib/PcbDoc ``Data`` streams are a flat sequence of primitive records, each
framed as ``[type:1][len:4 LE][payload:len]``. The parser understands a fixed
set of type bytes (see :class:`PcbRecordType`); anything else used to be skipped
one byte at a time, which both dropped the record and desynced the parser onto
the following primitives.

:class:`AltiumPcbOpaqueRecord` captures such a record's exact bytes and re-emits
them unchanged, so the binary round-trip stays lossless and the surrounding
primitives keep parsing correctly. It is the binary-layer foundation the JSON
serdes work (issue #15) relies on for "anything in, anything out".
"""

import logging

from .altium_record_types import PcbPrimitive, PcbRecordType

log = logging.getLogger(__name__)


class AltiumPcbOpaqueRecord(PcbPrimitive):
    """
    An unrecognized PCB primitive preserved verbatim for round-tripping.

    The original type byte and the full record bytes (type + length + payload)
    are retained so :meth:`serialize_to_binary` can reproduce them exactly.

    Attributes:
        type_byte: The raw record type byte that was not recognized.
    """

    def __init__(self, type_byte: int = 0, raw: bytes = b"") -> None:
        super().__init__()
        self.type_byte: int = int(type_byte)
        # Base class re-emits ``_raw_binary`` verbatim from serialize_to_binary().
        self._raw_binary: bytes = bytes(raw)

    @property
    def record_type(self) -> PcbRecordType:
        """
        The raw record type byte.

        Returns the matching :class:`PcbRecordType` member when one happens to
        exist, otherwise the raw integer (these are unrecognized types by
        definition, so usually the latter).
        """
        try:
            return PcbRecordType(self.type_byte)
        except ValueError:
            return self.type_byte  # type: ignore[return-value]

    def parse_from_binary(self, data: bytes, offset: int = 0) -> int:
        """
        Capture an unrecognized record verbatim starting at ``offset``.

        All PCB primitives are framed ``[type:1][len:4 LE][payload:len]``. The
        span is clamped to the buffer so a truncated/corrupt tail still
        round-trips as a single opaque blob instead of desyncing the parser.

        Returns:
            Number of bytes consumed.
        """
        span = opaque_record_span(data, offset)
        self.type_byte = data[offset] if offset < len(data) else 0
        self._raw_binary = bytes(data[offset : offset + span])
        return span

    def serialize_to_binary(self) -> bytes:
        """Return the preserved record bytes unchanged."""
        return self._raw_binary

    def __repr__(self) -> str:
        return (
            f"<AltiumPcbOpaqueRecord type=0x{self.type_byte:02X} "
            f"bytes={len(self._raw_binary)}>"
        )


def opaque_record_span(data: bytes, offset: int) -> int:
    """
    Bytes spanned by a PCB primitive record at ``offset``.

    Uses the universal ``[type:1][len:4 LE][payload:len]`` framing. Clamped to
    the end of ``data`` so a truncated or corrupt record yields a single opaque
    tail blob rather than reading past the buffer.

    Args:
        data: The footprint ``Data`` stream bytes.
        offset: Offset of the record's type byte.

    Returns:
        Number of bytes the record occupies (>= 1 while bytes remain).
    """
    end = len(data)
    if offset >= end:
        return 0
    # Not enough room for the 4-byte length field: swallow the remaining tail.
    if offset + 5 > end:
        return end - offset
    length = int.from_bytes(data[offset + 1 : offset + 5], "little")
    span = 5 + length
    # Length runs past the buffer (corrupt): clamp to what's left.
    if offset + span > end:
        return end - offset
    return span
