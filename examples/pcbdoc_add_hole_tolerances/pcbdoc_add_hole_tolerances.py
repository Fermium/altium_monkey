from __future__ import annotations

import json
from pathlib import Path

from altium_monkey import AltiumPcbDoc, PadShape, PcbLayer

SAMPLE_DIR = Path(__file__).resolve().parent
EXAMPLES_ROOT = SAMPLE_DIR.parent
INPUT_PCBDOC = EXAMPLES_ROOT / "assets" / "pcbdoc" / "blank.PcbDoc"
OUTPUT_DIR = SAMPLE_DIR / "output"
OUTPUT_PCBDOC = OUTPUT_DIR / "pcbdoc_add_hole_tolerances.PcbDoc"
OUTPUT_MANIFEST = OUTPUT_DIR / "pcbdoc_add_hole_tolerances.json"


def _add_label(pcbdoc: AltiumPcbDoc, text: str, x_mils: float, y_mils: float) -> None:
    pcbdoc.add_text(
        text=text,
        position_mils=(x_mils, y_mils),
        height_mils=42.0,
        stroke_width_mils=6.0,
        layer=PcbLayer.TOP_OVERLAY,
    )


def _record(
    *,
    primitive: str,
    label: str,
    x_mils: float,
    y_mils: float,
    positive_mils: float | None,
    negative_mils: float | None,
) -> dict[str, object]:
    return {
        "primitive": primitive,
        "label": label,
        "x_mils": x_mils,
        "y_mils": y_mils,
        "hole_positive_tolerance_mils": positive_mils,
        "hole_negative_tolerance_mils": negative_mils,
    }


def build_pcbdoc(output_path: Path = OUTPUT_PCBDOC) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pcbdoc = AltiumPcbDoc.from_file(INPUT_PCBDOC)
    pcbdoc.set_outline_rectangle_mils(0.0, 0.0, 5600.0, 3600.0)
    pcbdoc.set_origin_to_outline_lower_left()

    _add_label(pcbdoc, "Pad/Via hole tolerance examples", 260.0, 3320.0)
    _add_label(pcbdoc, "Unset is the control case", 260.0, 3050.0)

    manifest_entries: list[dict[str, object]] = []

    pad_specs = [
        ("PAD-NA", 850.0, "unset", None, None),
        ("PAD-3-2", 1950.0, "+3 / -2 mil", 3.0, 2.0),
        ("PAD-4-1", 3050.0, "+4 / -1 mil slot", 4.0, 1.0),
    ]
    for designator, x_mils, label, positive_mils, negative_mils in pad_specs:
        _add_label(pcbdoc, label, x_mils - 230.0, 2380.0)
        pad = pcbdoc.add_pad(
            designator=designator,
            position_mils=(x_mils, 2200.0),
            width_mils=150.0,
            height_mils=150.0,
            layer=PcbLayer.MULTI_LAYER,
            shape=PadShape.CIRCLE,
            hole_size_mils=50.0,
            plated=True,
            net="HOLE_TOL_PAD",
            hole_positive_tolerance_mils=positive_mils,
            hole_negative_tolerance_mils=negative_mils,
            slot_length_mils=180.0 if "slot" in label else 0.0,
            slot_rotation_degrees=90.0 if "slot" in label else 0.0,
        )
        manifest_entries.append(
            _record(
                primitive="pad",
                label=designator,
                x_mils=pad.x_mils,
                y_mils=pad.y_mils,
                positive_mils=pad.hole_positive_tolerance_mils,
                negative_mils=pad.hole_negative_tolerance_mils,
            )
        )

    via_specs = [
        ("VIA-NA", 850.0, "unset", None, None),
        ("VIA-1.5-.5", 1950.0, "+1.5 / -0.5 mil", 1.5, 0.5),
        ("VIA-2.5-.25", 3050.0, "+2.5 / -0.25 mil", 2.5, 0.25),
    ]
    for label_name, x_mils, label, positive_mils, negative_mils in via_specs:
        _add_label(pcbdoc, label, x_mils - 250.0, 1220.0)
        via = pcbdoc.add_via(
            position_mils=(x_mils, 1050.0),
            diameter_mils=28.0,
            hole_size_mils=12.0,
            net="HOLE_TOL_VIA",
            hole_positive_tolerance_mils=positive_mils,
            hole_negative_tolerance_mils=negative_mils,
        )
        manifest_entries.append(
            _record(
                primitive="via",
                label=label_name,
                x_mils=via.x_mils,
                y_mils=via.y_mils,
                positive_mils=via.hole_positive_tolerance_mils,
                negative_mils=via.hole_negative_tolerance_mils,
            )
        )

    manifest = {
        "output_pcbdoc": output_path.name,
        "units": {
            "script_inputs": "mils",
            "raw_record_fields": "internal units, 10000 per mil",
        },
        "entries": manifest_entries,
    }

    pcbdoc.save(output_path)
    OUTPUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    output_path = build_pcbdoc()
    print(f"Wrote {output_path}")
    print(f"Wrote {OUTPUT_MANIFEST}")


if __name__ == "__main__":
    main()
