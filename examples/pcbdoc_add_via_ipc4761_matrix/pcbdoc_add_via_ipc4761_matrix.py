from __future__ import annotations

import json
from pathlib import Path

from altium_monkey import (
    AltiumPcbDoc,
    AltiumPcbVia,
    PcbIpc4761ViaType,
    PcbLayer,
    PcbViaStructureFeatureSide,
    PcbViaStructureFeatureType,
)

SAMPLE_DIR = Path(__file__).resolve().parent
EXAMPLES_ROOT = SAMPLE_DIR.parent
INPUT_PCBDOC = EXAMPLES_ROOT / "assets" / "pcbdoc" / "blank.PcbDoc"
OUTPUT_DIR = SAMPLE_DIR / "output"
OUTPUT_PCBDOC = OUTPUT_DIR / "pcbdoc_add_via_ipc4761_matrix.PcbDoc"
OUTPUT_MANIFEST = OUTPUT_DIR / "pcbdoc_add_via_ipc4761_matrix.json"

IU_PER_MIL = 10000

IPC_TYPES = [
    PcbIpc4761ViaType.NONE,
    PcbIpc4761ViaType.TYPE_1A_TENTING,
    PcbIpc4761ViaType.TYPE_1B_TENTING,
    PcbIpc4761ViaType.TYPE_2A_TENTING_AND_COVERING,
    PcbIpc4761ViaType.TYPE_2B_TENTING_AND_COVERING,
    PcbIpc4761ViaType.TYPE_3A_PLUGGING,
    PcbIpc4761ViaType.TYPE_3B_PLUGGING,
    PcbIpc4761ViaType.TYPE_4A_PLUGGING_AND_COVERING,
    PcbIpc4761ViaType.TYPE_4B_PLUGGING_AND_COVERING,
    PcbIpc4761ViaType.TYPE_5_FILLING,
    PcbIpc4761ViaType.TYPE_6A_FILLING_AND_COVERING,
    PcbIpc4761ViaType.TYPE_6B_FILLING_AND_COVERING,
    PcbIpc4761ViaType.TYPE_7_FILLING_AND_CAPPING,
]

IPC_LABELS = {
    PcbIpc4761ViaType.NONE: "None",
    PcbIpc4761ViaType.TYPE_1A_TENTING: "Type1a",
    PcbIpc4761ViaType.TYPE_1B_TENTING: "Type1b",
    PcbIpc4761ViaType.TYPE_2A_TENTING_AND_COVERING: "Type2a",
    PcbIpc4761ViaType.TYPE_2B_TENTING_AND_COVERING: "Type2b",
    PcbIpc4761ViaType.TYPE_3A_PLUGGING: "Type3a",
    PcbIpc4761ViaType.TYPE_3B_PLUGGING: "Type3b",
    PcbIpc4761ViaType.TYPE_4A_PLUGGING_AND_COVERING: "Type4a",
    PcbIpc4761ViaType.TYPE_4B_PLUGGING_AND_COVERING: "Type4b",
    PcbIpc4761ViaType.TYPE_5_FILLING: "Type5",
    PcbIpc4761ViaType.TYPE_6A_FILLING_AND_COVERING: "Type6a",
    PcbIpc4761ViaType.TYPE_6B_FILLING_AND_COVERING: "Type6b",
    PcbIpc4761ViaType.TYPE_7_FILLING_AND_CAPPING: "Type7",
}


def _mils(value: float) -> int:
    return int(round(value * IU_PER_MIL))


def _add_label(pcbdoc: AltiumPcbDoc, text: str, x_mils: float, y_mils: float) -> None:
    pcbdoc.add_text(
        text=text,
        position_mils=(x_mils, y_mils),
        height_mils=45.0,
        stroke_width_mils=6.0,
        layer=PcbLayer.TOP_OVERLAY,
    )


def _via_row_entry(
    pcbdoc: AltiumPcbDoc,
    *,
    label: str,
    x_mils: float,
    y_mils: float,
    ipc_type: PcbIpc4761ViaType = PcbIpc4761ViaType.NONE,
    tent_top: bool = False,
    tent_bottom: bool = False,
) -> dict[str, object]:
    _add_label(pcbdoc, label, x_mils - 110.0, y_mils + 135.0)
    via = pcbdoc.add_via(
        position_mils=(x_mils, y_mils),
        diameter_mils=24.0,
        hole_size_mils=10.0,
        net="VIA_MODE_MATRIX",
        ipc4761_via_type=ipc_type,
        is_tent_top=tent_top,
        is_tent_bottom=tent_bottom,
    )
    return {
        "label": label,
        "x_mils": x_mils,
        "y_mils": y_mils,
        "ipc4761_via_type": int(via.ipc4761_via_type),
        "tent_top": via.is_tent_top,
        "tent_bottom": via.is_tent_bottom,
    }


def _set_manual_mask(
    via: AltiumPcbVia,
    *,
    front_mils: float,
    back_mils: float,
    linked: bool,
    from_hole_edge: bool = False,
) -> None:
    via.soldermask_expansion_manual = True
    via.soldermask_expansion_front = _mils(front_mils)
    via.soldermask_expansion_back = _mils(back_mils)
    via.soldermask_expansion_linked = linked
    via.soldermask_expansion_from_hole_edge = from_hole_edge


def _build_ipc_type_row(pcbdoc: AltiumPcbDoc) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    x0 = 650.0
    y = 4200.0
    x_step = 620.0

    _add_label(pcbdoc, "IPC-4761 type", 180.0, y + 135.0)
    for index, ipc_type in enumerate(IPC_TYPES):
        entries.append(
            _via_row_entry(
                pcbdoc,
                label=IPC_LABELS[ipc_type],
                x_mils=x0 + index * x_step,
                y_mils=y,
                ipc_type=ipc_type,
            )
        )
    return entries


def _build_tenting_and_mask_row(pcbdoc: AltiumPcbDoc) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    row_specs = [
        ("Tent top", True, False, None),
        ("Tent bot", False, True, None),
        ("Tent both", True, True, None),
        ("Manual 2/2", False, False, (2.0, 2.0, True, False)),
        ("Manual 4/8", False, False, (4.0, 8.0, False, False)),
        ("Hole edge", False, False, (5.0, 5.0, True, True)),
        ("Type7 epoxy", True, True, None),
    ]
    x0 = 900.0
    y = 2700.0
    x_step = 820.0

    _add_label(pcbdoc, "Tenting / mask", 180.0, y + 135.0)
    for index, (label, tent_top, tent_bottom, mask_spec) in enumerate(row_specs):
        ipc_type = (
            PcbIpc4761ViaType.TYPE_7_FILLING_AND_CAPPING
            if label == "Type7 epoxy"
            else PcbIpc4761ViaType.NONE
        )
        entry = _via_row_entry(
            pcbdoc,
            label=label,
            x_mils=x0 + index * x_step,
            y_mils=y,
            ipc_type=ipc_type,
            tent_top=tent_top,
            tent_bottom=tent_bottom,
        )
        via = pcbdoc.vias[-1]
        if mask_spec is not None:
            front, back, linked, from_hole_edge = mask_spec
            _set_manual_mask(
                via,
                front_mils=front,
                back_mils=back,
                linked=linked,
                from_hole_edge=from_hole_edge,
            )
            entry.update(
                {
                    "solder_mask_expansion_mode": via.solder_mask_expansion_mode,
                    "soldermask_expansion_front_mils": front,
                    "soldermask_expansion_back_mils": back,
                    "soldermask_expansion_linked": linked,
                    "soldermask_expansion_from_hole_edge": from_hole_edge,
                }
            )
        if label == "Type7 epoxy":
            via.set_ipc4761_feature_side(
                PcbViaStructureFeatureType.FILLING,
                PcbViaStructureFeatureSide.BOTH,
            )
            via.set_ipc4761_feature_material(
                PcbViaStructureFeatureType.FILLING,
                "EPOXY",
            )
            via.set_ipc4761_feature_side(
                PcbViaStructureFeatureType.CAPPING,
                PcbViaStructureFeatureSide.BOTH,
            )
            via.set_ipc4761_feature_material(
                PcbViaStructureFeatureType.CAPPING,
                "COPPER",
            )
            entry["ipc4761_material_intent"] = "EPOXY fill, COPPER cap"
        entries.append(entry)
    return entries


def build_pcbdoc(output_path: Path = OUTPUT_PCBDOC) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pcbdoc = AltiumPcbDoc.from_file(INPUT_PCBDOC)
    pcbdoc.set_outline_rectangle_mils(0.0, 0.0, 9000.0, 5200.0)
    pcbdoc.set_origin_to_outline_lower_left()
    _add_label(pcbdoc, "Via IPC-4761 matrix", 250.0, 4950.0)

    ipc_entries = _build_ipc_type_row(pcbdoc)
    mask_entries = _build_tenting_and_mask_row(pcbdoc)

    manifest = {
        "output_pcbdoc": output_path.name,
        "units": {
            "script_inputs": "mils",
            "low_level_mask_fields": "internal units, 10000 per mil",
        },
        "ipc_type_entries": ipc_entries,
        "tenting_and_mask_entries": mask_entries,
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
