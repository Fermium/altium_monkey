from __future__ import annotations

import json
import shutil
import struct
from pathlib import Path

from altium_monkey import (
    AltiumBoardOutline,
    AltiumDraftsmanDocument,
    AltiumPcbDoc,
    AltiumSchDoc,
    BoardOutlineVertex,
    ColorValue,
    DraftsmanColor,
    DraftsmanNoteBorderStyle,
    DraftsmanRect,
    DraftsmanStandardSheetSize,
    PcbLayer,
    SchFontSpec,
    SchPointMils,
    SchRectMils,
    make_sch_embedded_image,
    make_sch_text_string,
)
from altium_monkey.altium_prjpcb import AltiumPrjPcb


SAMPLE_DIR = Path(__file__).resolve().parent
PROJECT_NAME = "HELLO-DRAFTSMAN"

ASSET_PATH = SAMPLE_DIR / "assets" / "monkey.png"
OUTPUT_DIR = SAMPLE_DIR / "output"
PROJECT_DIR = OUTPUT_DIR
PRJPCB_NAME = f"{PROJECT_NAME}.PrjPcb"
SCHDOC_NAME = f"{PROJECT_NAME}.SchDoc"
PCBDOC_NAME = f"{PROJECT_NAME}.PcbDoc"
DRAFTSMAN_NAME = f"{PROJECT_NAME}.PCBDwf"

BOARD_WIDTH_MILS = 4000.0
BOARD_HEIGHT_MILS = 2500.0
DRAFTSMAN_NOTE_LEFT_MM = 6.0
DRAFTSMAN_NOTE_TOP_MM = 31.0
DRAFTSMAN_IMAGE_LEFT_MM = 3.0
DRAFTSMAN_IMAGE_BOTTOM_MM = 113.64583333333331
DRAFTSMAN_IMAGE_SIZE_MM = 115.85416666666663


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"expected a PNG image: {path}")
    return struct.unpack(">II", data[16:24])


def make_rectangular_outline_mils(
    width_mils: float,
    height_mils: float,
) -> AltiumBoardOutline:
    """Create board-outline vertices with the origin at the lower left."""

    return AltiumBoardOutline(
        vertices=[
            BoardOutlineVertex.line(0.0, 0.0),
            BoardOutlineVertex.line(width_mils, 0.0),
            BoardOutlineVertex.line(width_mils, height_mils),
            BoardOutlineVertex.line(0.0, height_mils),
        ]
    )


def build_schdoc(project_dir: Path) -> Path:
    schdoc = AltiumSchDoc()
    schdoc.add_object(
        make_sch_text_string(
            location_mils=SchPointMils.from_mils(1000, 1000),
            text="altium-monkey wuz here",
            font=SchFontSpec(name="Arial", size=18, bold=True),
            color=ColorValue.from_hex("#000000"),
        )
    )
    schdoc.add_object(
        make_sch_embedded_image(
            bounds_mils=SchRectMils.from_corners_mils(1000, 1200, 1800, 2000),
            source_path=ASSET_PATH,
            filename=ASSET_PATH.name,
            keep_aspect=True,
        )
    )

    output_path = project_dir / SCHDOC_NAME
    schdoc.save(output_path)
    return output_path


def build_pcbdoc(project_dir: Path) -> Path:
    pcbdoc = AltiumPcbDoc()
    board_outline = make_rectangular_outline_mils(BOARD_WIDTH_MILS, BOARD_HEIGHT_MILS)
    pcbdoc.set_board_outline(board_outline)
    pcbdoc.set_origin_to_outline_lower_left()
    pcbdoc.add_text(
        text="altium-monkey wuz here",
        position_mils=(250.0, 2250.0),
        height_mils=150.0,
        stroke_width_mils=18.0,
        layer=PcbLayer.TOP_OVERLAY,
    )

    output_path = project_dir / PCBDOC_NAME
    pcbdoc.save(output_path)
    return output_path


def build_draftsman(project_dir: Path, pcbdoc_path: Path) -> Path:
    document = AltiumDraftsmanDocument.blank(
        profile="ad25",
        source_document_name=pcbdoc_path.name,
    )
    document.document_options.grid_color = DraftsmanColor.rgb(243, 243, 243)

    font = document.get_or_create_font_style("Comic Sans MS", 14)
    title_font = document.get_or_create_font_style("Comic Sans MS", 60, bold=True)
    document.document_options.set_font_style(font)

    page = document.pages[0]
    page.apply_standard_sheet_size(DraftsmanStandardSheetSize.A3)
    upper_left = page.point_from_top_left(
        left_mm=DRAFTSMAN_NOTE_LEFT_MM,
        top_mm=DRAFTSMAN_NOTE_TOP_MM,
    )

    note = page.add_note(
        title="altium monkey wuz here",
        x_mm=upper_left.x_mm,
        y_mm=upper_left.y_mm,
        width_mm=250.0,
        bullets=(
            "This PCBDwf was synthesized from Python.",
            "The linked board is HELLO-DRAFTSMAN.PcbDoc.",
            "The project also contains a generated schematic.",
        ),
        element_font_style=font,
        title_font_style=title_font,
        bullet_border_style=DraftsmanNoteBorderStyle.CIRCLE,
    )
    note.add_element(
        "Placed 6 mm from the left edge and 31 mm from the top edge.",
        border_style=DraftsmanNoteBorderStyle.FLAG,
    )

    _png_size(ASSET_PATH)
    page.add_picture(
        source_path=ASSET_PATH,
        rect=DraftsmanRect(
            x_mm=DRAFTSMAN_IMAGE_LEFT_MM,
            y_mm=DRAFTSMAN_IMAGE_BOTTOM_MM,
            width_mm=DRAFTSMAN_IMAGE_SIZE_MM,
            height_mm=DRAFTSMAN_IMAGE_SIZE_MM,
        ),
        maintain_aspect_ratio=True,
    )

    output_path = project_dir / DRAFTSMAN_NAME
    document.save(output_path)
    return output_path


def build_project(project_dir: Path, document_paths: list[Path]) -> Path:
    project = AltiumPrjPcb.create_minimal(PROJECT_NAME)
    project.set_parameters(
        {
            "PROJECT_TITLE": "HELLO-DRAFTSMAN",
            "ENGINEER": "altium-monkey",
        }
    )
    for document_path in document_paths:
        project.add_document(document_path.name)

    output_path = project_dir / PRJPCB_NAME
    project.save(output_path)
    return output_path


def write_manifest(
    *,
    project_dir: Path,
    prjpcb_path: Path,
    schdoc_path: Path,
    pcbdoc_path: Path,
    draftsman_path: Path,
) -> Path:
    manifest_path = project_dir / "project_manifest.json"
    manifest = {
        "project": prjpcb_path.name,
        "documents": [
            schdoc_path.name,
            pcbdoc_path.name,
            draftsman_path.name,
        ],
        "draftsman": {
            "file": draftsman_path.name,
            "profile": "ad25",
            "source_document_name": pcbdoc_path.name,
            "sheet_size": "A3",
            "note_origin": "lower-left page coordinates",
            "note_top_left_offset_mm": {
                "left": DRAFTSMAN_NOTE_LEFT_MM,
                "top": DRAFTSMAN_NOTE_TOP_MM,
            },
            "note_title": "altium monkey wuz here",
            "note_font": "Comic Sans MS",
            "embedded_image": ASSET_PATH.name,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def reset_project_dir() -> None:
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    for child in PROJECT_DIR.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> None:
    reset_project_dir()
    schdoc_path = build_schdoc(PROJECT_DIR)
    pcbdoc_path = build_pcbdoc(PROJECT_DIR)
    draftsman_path = build_draftsman(PROJECT_DIR, pcbdoc_path)
    prjpcb_path = build_project(
        PROJECT_DIR,
        [schdoc_path, pcbdoc_path, draftsman_path],
    )
    manifest_path = write_manifest(
        project_dir=PROJECT_DIR,
        prjpcb_path=prjpcb_path,
        schdoc_path=schdoc_path,
        pcbdoc_path=pcbdoc_path,
        draftsman_path=draftsman_path,
    )

    print(f"Wrote project: {prjpcb_path.relative_to(SAMPLE_DIR)}")
    print(f"Wrote schematic: {schdoc_path.relative_to(SAMPLE_DIR)}")
    print(f"Wrote PCB: {pcbdoc_path.relative_to(SAMPLE_DIR)}")
    print(f"Wrote Draftsman: {draftsman_path.relative_to(SAMPLE_DIR)}")
    print(f"Wrote manifest: {manifest_path.relative_to(SAMPLE_DIR)}")


if __name__ == "__main__":
    main()
