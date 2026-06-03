"""
Regression tests for ``AltiumSchLib.apply_json`` colour edits.

GH issue #8: ``/schlib/edit`` (which calls ``apply_json``) silently no-op'd a
colour edit for STM32G071KBT6 — a symbol whose binary has a ``Component`` + a
``Rectangle`` body and 32 pins. Two compounding bugs:

1. ``_update_from_json`` used an all-or-nothing positional ``zip`` guarded by a
   bare object-count equality check: any mismatch (e.g. the caller's payload
   carrying a ``Parameter`` the binary doesn't have) skipped the WHOLE symbol.
2. ``apply_json`` patched ``raw_records`` but the parsed OOP objects kept their
   stale colours, so ``save()``'s OOP→raw re-sync reverted the edit.

These tests pin the fixed behaviour: edits apply (and survive save) even when
the payload count differs, and a sparse single-object patch works.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from altium_monkey.altium_schlib import AltiumSchLib

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "STM32G071KBT6.SchLib"

# Delphi/Altium colours are stored as integers (0x00BBGGRR).
RED = 255  # 0x0000FF -> renders #FF0000
GREEN = 65280  # 0x00FF00 -> renders #00FF00


def _symbol_json(lib: AltiumSchLib) -> dict:
    return lib.to_json()["Symbols"][0]


def _record_by_type(lib: AltiumSchLib, object_type: str) -> dict:
    """Return the raw record backing the first object of the given JSON type."""
    sym = _symbol_json(lib)
    idx = next(o["ObjectIndex"] for o in sym["Objects"] if o["ObjectType"] == object_type)
    return lib.symbols[0].raw_records[idx]


def _save_and_reload(lib: AltiumSchLib) -> AltiumSchLib:
    with tempfile.TemporaryDirectory(prefix="schlib_recolor_test_") as tmp:
        out = Path(tmp) / "out.SchLib"
        lib.save(out)
        return AltiumSchLib(out)


def test_fixture_shape() -> None:
    """Guards the assumptions the other tests rely on: a Component + Rectangle
    body, 32 pins, and no Parameter record in the binary."""
    lib = AltiumSchLib(str(FIXTURE))
    sym = _symbol_json(lib)
    counts: dict[str, int] = {}
    for obj in sym["Objects"]:
        counts[obj["ObjectType"]] = counts.get(obj["ObjectType"], 0) + 1
    assert counts.get("Component") == 1
    assert counts.get("Rectangle") == 1
    assert counts.get("Pin") == 32
    assert "Parameter" not in counts  # the binary has none — the trigger for #8


def test_recolor_survives_extra_object_in_payload() -> None:
    """The exact #8 repro: recolour the body, append a Parameter the binary
    lacks (count 37 vs 36), and confirm the edit is applied and persists through
    save — instead of the whole symbol being silently dropped."""
    lib = AltiumSchLib(str(FIXTURE))
    sym = _symbol_json(lib)
    objects = sym["Objects"]
    for obj in objects:
        if obj["ObjectType"] in ("Rectangle", "Component"):
            obj["Color"] = GREEN
            obj["AreaColor"] = RED
    # Caller appends a Parameter with no counterpart in the binary.
    objects.append({"ObjectType": "Parameter", "Name": "Value", "Color": RED})

    lib.apply_json({"Symbols": [{"Name": sym["Name"], "Objects": objects}]})

    reloaded = _save_and_reload(lib)
    rect = _record_by_type(reloaded, "Rectangle")
    comp = _record_by_type(reloaded, "Component")
    assert rect["Color"] == str(GREEN)
    assert rect["AreaColor"] == str(RED)
    assert comp["Color"] == str(GREEN)

    # And the recoloured body actually renders.
    svg = reloaded.symbol_to_svg(sym["Name"]).lower()
    assert "#00ff00" in svg  # border (GREEN)
    assert "#ff0000" in svg  # fill (RED)


def test_sparse_single_object_patch() -> None:
    """A payload of just the one record being changed — each carrying its
    ObjectIndex — patches only that record and leaves the rest untouched."""
    lib = AltiumSchLib(str(FIXTURE))
    rect_idx = next(
        o["ObjectIndex"] for o in _symbol_json(lib)["Objects"] if o["ObjectType"] == "Rectangle"
    )
    original_comp_color = _record_by_type(lib, "Component")["Color"]

    lib.apply_json(
        {
            "Symbols": [
                {
                    "Name": lib.symbols[0].name,
                    "Objects": [
                        {"ObjectType": "Rectangle", "ObjectIndex": rect_idx, "AreaColor": GREEN}
                    ],
                }
            ]
        }
    )

    reloaded = _save_and_reload(lib)
    assert _record_by_type(reloaded, "Rectangle")["AreaColor"] == str(GREEN)
    # The untouched Component keeps its original colour.
    assert _record_by_type(reloaded, "Component")["Color"] == original_comp_color


def test_identity_apply_is_lossless() -> None:
    """Re-applying a symbol's own to_json() output and saving must not perturb
    any record (including the 32 binary pin records)."""
    base = AltiumSchLib(str(FIXTURE))
    data = base.to_json()

    lib = AltiumSchLib(str(FIXTURE))
    lib.apply_json({"Symbols": [data["Symbols"][0]]})
    reloaded = _save_and_reload(lib)

    base_raw = base.symbols[0].raw_records
    new_raw = reloaded.symbols[0].raw_records
    assert len(base_raw) == len(new_raw)
    for before, after in zip(base_raw, new_raw, strict=True):
        if before.get("__BINARY_RECORD__"):
            assert bytes(before.get("__BINARY_DATA__") or b"") == bytes(
                after.get("__BINARY_DATA__") or b""
            )
        else:
            stripped_before = {k: v for k, v in before.items() if k != "__BINARY_RECORD__"}
            stripped_after = {k: v for k, v in after.items() if k != "__BINARY_RECORD__"}
            assert stripped_before == stripped_after


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
