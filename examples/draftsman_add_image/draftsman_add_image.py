from __future__ import annotations

import json
import shutil
import struct
from pathlib import Path

from altium_monkey import (
    AltiumDraftsmanDocument,
    DraftsmanColor,
    DraftsmanHorizontalAlignment,
    DraftsmanMargin,
    DraftsmanRect,
    DraftsmanStandardSheetSize,
    DraftsmanVerticalAlignment,
)


SAMPLE_DIR = Path(__file__).resolve().parent
ASSET_PATH = SAMPLE_DIR / "assets" / "monkey.png"
OUTPUT_DIR = SAMPLE_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "draftsman_add_image.PCBDwf"
SUMMARY_PATH = OUTPUT_DIR / "draftsman_add_image.json"
IMAGE_WIDTH_MM = 80.0
BORDER_ZONE_MARGIN_MM = 1.5


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"expected a PNG image: {path}")
    return struct.unpack(">II", data[16:24])


def build_draftsman(output_path: Path = OUTPUT_PATH) -> Path:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    document = AltiumDraftsmanDocument.blank(
        profile="ad25",
        source_document_name="draftsman_add_image.PcbDoc",
    )
    document.document_options.grid_color = DraftsmanColor.rgb(243, 243, 243)

    default_font = document.get_or_create_font_style("Arial", 8)
    document.document_options.set_font_style(default_font)
    text_font = document.get_or_create_font_style("Comic Sans MS", 24, bold=True)

    page = document.pages[0]
    page.apply_standard_sheet_size(DraftsmanStandardSheetSize.A3)
    page.margin = DraftsmanMargin(
        left_mm=BORDER_ZONE_MARGIN_MM,
        top_mm=BORDER_ZONE_MARGIN_MM,
        right_mm=BORDER_ZONE_MARGIN_MM,
        bottom_mm=BORDER_ZONE_MARGIN_MM,
    )

    source_width_px, source_height_px = _png_size(ASSET_PATH)
    image_height_mm = IMAGE_WIDTH_MM * source_height_px / source_width_px
    image_rect = page.rect_centered(
        width_mm=IMAGE_WIDTH_MM,
        height_mm=image_height_mm,
    )
    text_rect = DraftsmanRect(
        x_mm=image_rect.x_mm - 20.0,
        y_mm=image_rect.y_mm + image_rect.height_mm + 10.0,
        width_mm=image_rect.width_mm + 40.0,
        height_mm=12.0,
    )
    text = page.add_text(
        text="altium-monkey wuz here",
        rect=text_rect,
        font_style=text_font,
        color=DraftsmanColor.rgb(0, 0, 0),
        horizontal_alignment=DraftsmanHorizontalAlignment.CENTER,
        vertical_alignment=DraftsmanVerticalAlignment.CENTER,
    )
    picture = page.add_picture(
        source_path=ASSET_PATH,
        rect=image_rect,
        maintain_aspect_ratio=True,
    )

    document.save(output_path)
    reloaded = AltiumDraftsmanDocument.from_file(output_path)
    summary = {
        "output": output_path.name,
        "asset": ASSET_PATH.name,
        "source_image_px": {
            "width": source_width_px,
            "height": source_height_px,
        },
        "sheet_size": "A3",
        "coordinate_origin": "lower-left",
        "border_zone_margin_mm": BORDER_ZONE_MARGIN_MM,
        "document_default_font": {
            "family": default_font.family_name,
            "size": default_font.size,
        },
        "text_font": {
            "family": text_font.family_name,
            "size": text_font.size,
            "bold": text_font.bold,
        },
        "text_id": text.id,
        "picture_id": picture.id,
        "text_rect_mm": text_rect.__dict__,
        "image_rect_mm": image_rect.__dict__,
        "text_count": len(reloaded.texts),
        "picture_count": len(reloaded.pictures),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    output_path = build_draftsman()
    print(f"Wrote {output_path.relative_to(SAMPLE_DIR)}")
    print(f"Wrote {SUMMARY_PATH.relative_to(SAMPLE_DIR)}")


if __name__ == "__main__":
    main()
