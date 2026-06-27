"""
Tests for the read-only PCB connection (ratsnest) model parsed from
``Connections6/Data``.

The connection format is verified structurally (against parsed pad/via centres
and net indices on a real board) and for byte-exact round-trip. The document
serializer preserves ``Connections6/Data`` verbatim, so parsing must not change
what is written back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from altium_monkey import AltiumPcbConnection, AltiumPcbDoc
from altium_monkey.altium_ole import AltiumOleFile
from altium_monkey.altium_record_pcb__connection import parse_connections6_stream

_REPO = Path(__file__).resolve().parents[1]
# m2_emmc is the corpus board with a non-empty Connections6/Data stream.
_M2_EMMC = _REPO / "examples" / "assets" / "projects" / "m2_emmc" / "m2_emmc.PcbDoc"


def _connections_stream(path: Path) -> bytes:
    return bytes(AltiumOleFile(str(path)).openstream(["Connections6", "Data"]))


@pytest.mark.skipif(not _M2_EMMC.exists(), reason="m2_emmc fixture not present")
def test_connections_parsed_from_board() -> None:
    doc = AltiumPcbDoc.from_file(str(_M2_EMMC))
    assert len(doc.connections) == 25
    assert all(isinstance(c, AltiumPcbConnection) for c in doc.connections)


@pytest.mark.skipif(not _M2_EMMC.exists(), reason="m2_emmc fixture not present")
def test_connection_endpoints_match_pad_via_centres() -> None:
    """
    Each ratsnest endpoint should sit on a pad or via centre carrying the same
    net index. This cross-checks the decoded coordinate offsets and net field
    against the independently-parsed pad/via geometry.
    """
    doc = AltiumPcbDoc.from_file(str(_M2_EMMC))
    centres: dict[tuple[int, int], int | None] = {}
    for pad in doc.pads:
        centres[(pad.x, pad.y)] = getattr(pad, "net_index", None)
    for via in doc.vias:
        centres[(via.x, via.y)] = getattr(via, "net_index", None)

    total = matched = net_consistent = 0
    for conn in doc.connections:
        for ex, ey in ((conn.x1, conn.y1), (conn.x2, conn.y2)):
            total += 1
            if (ex, ey) in centres:
                matched += 1
                if centres[(ex, ey)] == conn.net_index:
                    net_consistent += 1

    # The vast majority of endpoints land exactly on a pad/via centre; a few may
    # terminate on routed copper. Every matched endpoint must be net-consistent.
    assert matched >= int(0.9 * total)
    assert net_consistent == matched


@pytest.mark.skipif(not _M2_EMMC.exists(), reason="m2_emmc fixture not present")
def test_connections_roundtrip_byte_exact() -> None:
    original = _connections_stream(_M2_EMMC)
    parsed = parse_connections6_stream(original)
    rebuilt = b"".join(c.to_bytes() for c in parsed)
    assert rebuilt == original


@pytest.mark.skipif(not _M2_EMMC.exists(), reason="m2_emmc fixture not present")
def test_document_save_preserves_connections(tmp_path: Path) -> None:
    original = _connections_stream(_M2_EMMC)
    doc = AltiumPcbDoc.from_file(str(_M2_EMMC))
    out = tmp_path / "roundtrip.PcbDoc"
    doc.save(str(out))
    assert _connections_stream(out) == original


def test_parse_tolerates_truncated_trailing_block() -> None:
    """A truncated final block stops iteration rather than raising."""
    # One valid 4-byte content block, then a length prefix that overruns.
    good = b"\x04\x00\x00\x00" + b"\x4b\x00\x00\x00"
    truncated = good + b"\x40\x00\x00\x00" + b"\x01\x02"
    parsed = parse_connections6_stream(truncated)
    assert len(parsed) == 1
    assert parsed[0].raw_content == b"\x4b\x00\x00\x00"


def test_unlinked_sentinels_become_none() -> None:
    content = bytearray(29)
    content[3:5] = (0xFFFF).to_bytes(2, "little")  # net
    content[7:9] = (0xFFFF).to_bytes(2, "little")  # component
    conn = AltiumPcbConnection.from_content(bytes(content))
    assert conn.net_index is None
    assert conn.component_index is None
