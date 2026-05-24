from __future__ import annotations

import json
from pathlib import Path

from altium_monkey import AltiumPcbDoc, PcbLayer

SAMPLE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SAMPLE_DIR / "output"
OUTPUT_PCBDOC = OUTPUT_DIR / "pcbdoc_add_differential_pairs.PcbDoc"
OUTPUT_MANIFEST = OUTPUT_DIR / "pcbdoc_add_differential_pairs.json"

BOARD_WIDTH_MILS = 7200.0
BOARD_HEIGHT_MILS = 4200.0


def _add_label(pcbdoc: AltiumPcbDoc, text: str, x_mils: float, y_mils: float) -> None:
    pcbdoc.add_text(
        text=text,
        position_mils=(x_mils, y_mils),
        height_mils=70.0,
        stroke_width_mils=8.0,
        layer=PcbLayer.TOP_OVERLAY,
    )


def _route_pair(
    pcbdoc: AltiumPcbDoc,
    *,
    pair_name: str,
    positive_net: str,
    negative_net: str,
    y_mils: float,
    gather_control: bool = False,
) -> None:
    pcbdoc.add_differential_pair(
        name=pair_name,
        positive_net_name=positive_net,
        negative_net_name=negative_net,
        gather_control=gather_control,
    )
    _add_label(
        pcbdoc,
        f"{pair_name}: {positive_net} / {negative_net}",
        550.0,
        y_mils + 170.0,
    )

    pcbdoc.add_track(
        (900.0, y_mils + 36.0),
        (6100.0, y_mils + 36.0),
        width_mils=5.0,
        layer=PcbLayer.TOP,
        net=positive_net,
    )
    pcbdoc.add_track(
        (900.0, y_mils - 36.0),
        (6100.0, y_mils - 36.0),
        width_mils=5.0,
        layer=PcbLayer.TOP,
        net=negative_net,
    )
    pcbdoc.add_via(
        position_mils=(6325.0, y_mils + 36.0),
        diameter_mils=22.0,
        hole_size_mils=10.0,
        net=positive_net,
    )
    pcbdoc.add_via(
        position_mils=(6325.0, y_mils - 36.0),
        diameter_mils=22.0,
        hole_size_mils=10.0,
        net=negative_net,
    )


def _pair_row(pair: object) -> dict[str, object]:
    return {
        "name": str(getattr(pair, "name", "")),
        "positive_net_name": str(getattr(pair, "positive_net_name", "")),
        "negative_net_name": str(getattr(pair, "negative_net_name", "")),
        "gather_control": bool(getattr(pair, "gather_control", False)),
        "unique_id": str(getattr(pair, "unique_id", "")),
    }


def build_pcbdoc(output_path: Path = OUTPUT_PCBDOC) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pcbdoc = AltiumPcbDoc()
    pcbdoc.set_outline_rectangle_mils(
        0.0,
        0.0,
        BOARD_WIDTH_MILS,
        BOARD_HEIGHT_MILS,
    )
    pcbdoc.set_origin_to_outline_lower_left()
    _add_label(pcbdoc, "Differential pair authoring", 400.0, 3920.0)

    _route_pair(
        pcbdoc,
        pair_name="USB_D",
        positive_net="USB_D_P",
        negative_net="USB_D_N",
        y_mils=3000.0,
    )
    _route_pair(
        pcbdoc,
        pair_name="CAM_D0",
        positive_net="CAM_D0_P",
        negative_net="CAM_D0_N",
        y_mils=2100.0,
        gather_control=True,
    )
    _route_pair(
        pcbdoc,
        pair_name="LVDS_CLK",
        positive_net="LVDS_CLK_P",
        negative_net="LVDS_CLK_N",
        y_mils=1200.0,
    )

    pcbdoc.save(output_path)

    reparsed = AltiumPcbDoc.from_file(output_path)
    manifest = {
        "output_pcbdoc": output_path.name,
        "source": "created from AltiumPcbDoc() without an input PcbDoc",
        "units": "mils",
        "differential_pair_count": len(reparsed.differential_pairs),
        "net_count": len(reparsed.nets),
        "track_count": len(reparsed.tracks),
        "via_count": len(reparsed.vias),
        "pairs": [_pair_row(pair) for pair in reparsed.differential_pairs],
    }
    OUTPUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    output_path = build_pcbdoc()
    print(f"Wrote {output_path}")
    print(f"Wrote {OUTPUT_MANIFEST}")


if __name__ == "__main__":
    main()
