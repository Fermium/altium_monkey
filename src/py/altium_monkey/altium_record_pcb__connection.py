"""
Typed PCB connection (ratsnest) model for Connections6/Data.

A *connection* is an unrouted guidance line ("ratsnest") joining two points on
the same net. It is derived connectivity rather than placed copper: Altium
regenerates it from the netlist, so this module exposes a read-only view for
connectivity inspection. The underlying ``Connections6/Data`` stream is still
round-tripped verbatim by the document serializer; parsing it here does not
change what is written back.

Stream framing (homogeneous, no per-record type byte)::

    repeat: [uint32 content_len][content]

The ``content`` block is the shared PCB graphical-object layout also used by
fills::

    off 0      uint8   layer
    off 1      uint8   flags1
    off 2      uint8   flags2
    off 3-4    uint16  net_index        (0xFFFF = unlinked)
    off 5-6    uint16  polygon_index    (0xFFFF = none)
    off 7-8    uint16  component_index  (0xFFFF = unlinked)
    off 9-12   uint32  union_index      (0xFFFFFFFF = none)
    off 13-20  int32x2 endpoint 1 (x1, y1)   internal units (10,000/mil)
    off 21-28  int32x2 endpoint 2 (x2, y2)
    off 29..   bytes   trailing fields (preserved verbatim)

The endpoint coordinates and ``net_index`` were verified against parsed pad/via
centres and net indices on a real board (every matched endpoint sits on a pad or
via centre carrying the same net index).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import struct

_UNLINKED_U16 = 0xFFFF
_NO_UNION_U32 = 0xFFFFFFFF

# Fixed offset of the first endpoint coordinate inside the content block.
_ENDPOINT_OFFSET = 13
# Minimum content length needed to read both endpoints (13 + 2 * 8).
_MIN_CONTENT_LEN = 29


@dataclass
class AltiumPcbConnection:
    """
    A single PCB ratsnest connection between two points on one net.

    Coordinates are in Altium internal units (10,000 units per mil). Use the
    ``*_mils`` properties for mil values. ``net_index`` / ``component_index`` are
    ``None`` when the field carries the unlinked sentinel (0xFFFF).
    """

    layer: int = 0
    flags1: int = 0
    flags2: int = 0
    net_index: int | None = None
    polygon_index: int = _UNLINKED_U16
    component_index: int | None = None
    union_index: int = _NO_UNION_U32
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0
    # Full content block, retained so the record can be re-emitted byte-exact.
    raw_content: bytes = field(default=b"", repr=False)

    @classmethod
    def _from_internal_units(cls, value: int) -> float:
        """
        Convert internal units (10,000/mil) to mils.
        """
        return value / 10000.0

    @property
    def x1_mils(self) -> float:
        """Endpoint 1 X in mils."""
        return self._from_internal_units(self.x1)

    @property
    def y1_mils(self) -> float:
        """Endpoint 1 Y in mils."""
        return self._from_internal_units(self.y1)

    @property
    def x2_mils(self) -> float:
        """Endpoint 2 X in mils."""
        return self._from_internal_units(self.x2)

    @property
    def y2_mils(self) -> float:
        """Endpoint 2 Y in mils."""
        return self._from_internal_units(self.y2)

    @property
    def length_internal(self) -> float:
        """Straight-line ratsnest length in internal units."""
        return float(((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2) ** 0.5)

    @property
    def length_mils(self) -> float:
        """Straight-line ratsnest length in mils."""
        return self._from_internal_units(self.length_internal)

    @classmethod
    def from_content(cls, content: bytes) -> "AltiumPcbConnection":
        """
        Build a connection from a single content block (without the length
        prefix). Short or malformed blocks are tolerated: unreadable fields keep
        their defaults and the raw bytes are retained for round-trip.
        """
        obj = cls(raw_content=bytes(content))
        if len(content) >= 13:
            obj.layer = content[0]
            obj.flags1 = content[1]
            obj.flags2 = content[2]
            net = struct.unpack_from("<H", content, 3)[0]
            obj.net_index = None if net == _UNLINKED_U16 else net
            obj.polygon_index = struct.unpack_from("<H", content, 5)[0]
            comp = struct.unpack_from("<H", content, 7)[0]
            obj.component_index = None if comp == _UNLINKED_U16 else comp
            obj.union_index = struct.unpack_from("<I", content, 9)[0]
        if len(content) >= _MIN_CONTENT_LEN:
            obj.x1, obj.y1, obj.x2, obj.y2 = struct.unpack_from(
                "<iiii", content, _ENDPOINT_OFFSET
            )
        return obj

    def to_bytes(self) -> bytes:
        """
        Re-emit the length-prefixed record. Returns the preserved raw content so
        round-trips are byte-exact for parsed records.
        """
        return struct.pack("<I", len(self.raw_content)) + self.raw_content

    def __repr__(self) -> str:
        net = "?" if self.net_index is None else self.net_index
        return (
            f"<AltiumPcbConnection net={net} "
            f"({self.x1_mils:.2f}, {self.y1_mils:.2f})->"
            f"({self.x2_mils:.2f}, {self.y2_mils:.2f}) "
            f"len={self.length_mils:.1f}mil>"
        )


def parse_connections6_stream(data: bytes) -> list[AltiumPcbConnection]:
    """
    Parse a ``Connections6/Data`` stream into connection records.

    The stream is a sequence of ``[uint32 length][content]`` blocks. Parsing is
    defensive: a truncated trailing block stops iteration rather than raising.
    """
    out: list[AltiumPcbConnection] = []
    buf = bytes(data)
    offset = 0
    n = len(buf)
    while offset + 4 <= n:
        content_len = struct.unpack_from("<I", buf, offset)[0]
        start = offset + 4
        end = start + content_len
        if end > n:
            break
        out.append(AltiumPcbConnection.from_content(buf[start:end]))
        offset = end
    return out
