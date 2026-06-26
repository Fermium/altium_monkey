"""
Regression tests for verbatim preservation of unknown PcbLib primitive records.

PcbLib ``Data`` streams are a flat sequence of primitives framed as
``[type:1][len:4 LE][payload:len]``. The footprint parser only recognizes a
fixed set of type bytes; previously any other type was skipped one byte at a
time, which dropped the record AND desynced the parser onto the following
primitives (silently corrupting an otherwise lossless binary round-trip).

These tests pin the fixed behaviour: an unrecognized record is captured as an
:class:`AltiumPcbOpaqueRecord`, re-emitted byte-for-byte, the surrounding
primitives keep parsing, and a corrupt/truncated record clamps to the buffer.
"""

from __future__ import annotations

import glob
import struct
from pathlib import Path

import pytest

from altium_monkey.altium_pcblib import AltiumPcbFootprint, AltiumPcbLib
from altium_monkey.altium_record_pcb__opaque import (
    AltiumPcbOpaqueRecord,
    opaque_record_span,
)

_REPO = Path(__file__).resolve().parents[1]
_FIXTURES = sorted(glob.glob(str(_REPO / "examples" / "assets" / "pcblib" / "*.PcbLib")))


def _footprint_name_header(name: str) -> bytes:
    """Build the ``[uint32 len][pascal-string]`` header a Data stream starts with."""
    pascal = bytes([len(name)]) + name.encode("ascii")
    return struct.pack("<I", len(pascal)) + pascal


def _first_track_bytes() -> bytes:
    """Serialized bytes of a real TRACK primitive from a fixture."""
    if not _FIXTURES:
        pytest.skip("no PcbLib fixtures available")
    lib = AltiumPcbLib.from_file(_FIXTURES[0])
    for fp in lib.footprints:
        if fp.tracks:
            trk = fp.tracks[0].serialize_to_binary()
            assert trk[0] == 4  # TRACK type byte
            return trk
    pytest.skip("no fixture footprint with a track")


@pytest.mark.skipif(not _FIXTURES, reason="no PcbLib fixtures available")
def test_normal_fixtures_have_no_opaque_records() -> None:
    """Real libraries contain only known types -> no spurious opaque capture."""
    for fixture in _FIXTURES[:6]:
        lib = AltiumPcbLib.from_file(fixture)
        for fp in lib.footprints:
            assert not fp.opaque_records, f"{fixture}:{fp.name} captured opaque records"


def test_unknown_record_preserved_and_neighbours_stay_in_sync() -> None:
    """An unknown record round-trips verbatim and does not desync the parser."""
    trk = _first_track_bytes()
    payload = bytes(range(40))
    unknown = bytes([0x0D]) + struct.pack("<I", len(payload)) + payload  # type 0x0D

    name = "TEST_FP"
    stream = _footprint_name_header(name) + trk + unknown + trk

    fp = AltiumPcbFootprint(name)
    fp.parse_binary_data(stream)

    # Both real tracks parsed despite the unknown record between them.
    assert len(fp.tracks) == 2
    assert len(fp.opaque_records) == 1
    opaque = fp.opaque_records[0]
    assert opaque.type_byte == 0x0D
    assert opaque.serialize_to_binary() == unknown
    assert [type(p).__name__ for p in fp._record_order] == [
        "AltiumPcbTrack",
        "AltiumPcbOpaqueRecord",
        "AltiumPcbTrack",
    ]

    # Whole Data stream reproduced byte-for-byte.
    assert fp.serialize_data_stream() == stream


def test_truncated_unknown_record_clamps_to_buffer() -> None:
    """A corrupt length must clamp to EOF, not read past or crash."""
    trk = _first_track_bytes()
    name = "T2"
    # Declared length (9999) runs far past the end of the stream.
    bad = _footprint_name_header(name) + trk + bytes([0x0D]) + struct.pack("<I", 9999)

    fp = AltiumPcbFootprint(name)
    fp.parse_binary_data(bad)

    assert len(fp.opaque_records) == 1
    assert fp.serialize_data_stream() == bad


def test_opaque_record_span_edge_cases() -> None:
    assert opaque_record_span(b"", 0) == 0
    # Type byte present but no room for the 4-byte length -> swallow the tail.
    assert opaque_record_span(b"\x0d\x02", 0) == 2
    # Well-formed record: 1 type + 4 length + payload.
    payload = b"\xaa" * 6
    rec = bytes([0x0D]) + struct.pack("<I", len(payload)) + payload
    assert opaque_record_span(rec, 0) == len(rec)


def test_opaque_record_parse_returns_span() -> None:
    payload = b"\x01\x02\x03"
    rec = bytes([0x42]) + struct.pack("<I", len(payload)) + payload
    op = AltiumPcbOpaqueRecord()
    consumed = op.parse_from_binary(rec, 0)
    assert consumed == len(rec)
    assert op.type_byte == 0x42
    assert op.serialize_to_binary() == rec
