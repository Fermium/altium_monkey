from __future__ import annotations

import json
import shutil
from pathlib import Path

from altium_monkey import (
    AltiumDraftsmanDocument,
    AltiumPcbDoc,
    AltiumSchDoc,
    DraftsmanColor,
    DraftsmanRect,
    DraftsmanStandardSheetSize,
)
from altium_monkey.altium_prjpcb import AltiumPrjPcb


SAMPLE_DIR = Path(__file__).resolve().parent
EXAMPLES_ROOT = SAMPLE_DIR.parent
PROJECT_NAME = "draftsman_multipage_notes"

OUTPUT_DIR = SAMPLE_DIR / "output"
OUTPUT_PROJECT = OUTPUT_DIR / f"{PROJECT_NAME}.PrjPcb"
OUTPUT_SCHDOC = OUTPUT_DIR / f"{PROJECT_NAME}.SchDoc"
OUTPUT_PCBDOC = OUTPUT_DIR / f"{PROJECT_NAME}.PcbDoc"
OUTPUT_DRAFTSMAN = OUTPUT_DIR / f"{PROJECT_NAME}.PCBDwf"
SUMMARY_PATH = OUTPUT_DIR / "draftsman_multipage_notes.json"


def _relative_to_examples(path: Path) -> str:
    return path.resolve().relative_to(EXAMPLES_ROOT.resolve()).as_posix()


def _reset_output_dir() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _write_empty_project_documents() -> None:
    AltiumSchDoc().save(OUTPUT_SCHDOC)
    AltiumPcbDoc().save(OUTPUT_PCBDOC)


def _write_project(document_paths: list[Path]) -> None:
    project = AltiumPrjPcb.create_minimal(PROJECT_NAME)
    project.set_parameters(
        {
            "PROJECT_TITLE": "Draftsman Multipage Notes",
            "ENGINEER": "altium-monkey",
        }
    )
    for document_path in document_paths:
        project.add_document(document_path.name)
    project.save(OUTPUT_PROJECT)


def _note_summary(note_id: int, document: AltiumDraftsmanDocument) -> dict[str, object]:
    note = document.note_by_id(note_id)
    if note is None:
        raise ValueError(f"missing Draftsman note id {note_id}")
    return {
        "id": note.id,
        "page_id": note.page.id,
        "title": note.title,
        "row_ids": [row.id for row in note.elements],
        "rows": [row.text for row in note.elements],
    }


def build_draftsman_project() -> dict[str, object]:
    _reset_output_dir()
    _write_empty_project_documents()

    document = AltiumDraftsmanDocument.blank(
        profile="ad25",
        source_document_name=OUTPUT_PCBDOC.name,
    )
    document.document_options.grid_color = DraftsmanColor.rgb(243, 243, 243)

    page_1 = document.pages[0]
    page_1.apply_standard_sheet_size(DraftsmanStandardSheetSize.A3)
    point_1 = page_1.point_from_top_left(left_mm=12.0, top_mm=18.0)
    note_1 = page_1.add_note(
        title="PAGE 1 NOTES",
        rect=DraftsmanRect(
            x_mm=point_1.x_mm,
            y_mm=point_1.y_mm,
            width_mm=145.0,
            height_mm=0.0,
        ),
        bullets=("This note lives on the original page.",),
    )

    page_2 = document.add_page(copy_from=page_1, clear_items=True)
    point_2 = page_2.point_from_top_left(left_mm=12.0, top_mm=18.0)
    note_2 = page_2.add_note(
        title="PAGE 2 NOTES",
        rect=DraftsmanRect(
            x_mm=point_2.x_mm,
            y_mm=point_2.y_mm,
            width_mm=145.0,
            height_mm=0.0,
        ),
        bullets=("This note lives on the cloned sheet setup.",),
    )
    page_2_id = page_2.id
    note_1_id = note_1.id
    note_2_id = note_2.id
    if page_2_id is None or note_1_id is None or note_2_id is None:
        raise ValueError("generated Draftsman pages and notes must have ids")

    document.save(OUTPUT_DRAFTSMAN)
    _write_project([OUTPUT_SCHDOC, OUTPUT_PCBDOC, OUTPUT_DRAFTSMAN])

    reloaded = AltiumDraftsmanDocument.from_file(OUTPUT_DRAFTSMAN)
    reloaded_project = AltiumPrjPcb(OUTPUT_PROJECT)
    page_2_lookup = reloaded.page_by_id(page_2_id)
    if page_2_lookup is None:
        raise ValueError(f"missing Draftsman page id {page_2_id}")
    page_2_scoped_note = page_2_lookup.note_by_title("page 2 notes")
    if page_2_scoped_note is None:
        raise ValueError("missing page-scoped Draftsman note")
    note_2_lookup = reloaded.note_by_id(note_2_id)
    if note_2_lookup is None:
        raise ValueError(f"missing Draftsman note id {note_2_id}")

    project_documents = [
        str(document_entry["path"]) for document_entry in reloaded_project.documents
    ]
    summary = {
        "output_dir": _relative_to_examples(OUTPUT_DIR),
        "output_prjpcb": _relative_to_examples(OUTPUT_PROJECT),
        "output_schdoc": _relative_to_examples(OUTPUT_SCHDOC),
        "output_pcbdoc": _relative_to_examples(OUTPUT_PCBDOC),
        "output_draftsman": _relative_to_examples(OUTPUT_DRAFTSMAN),
        "source_document_name": reloaded.source_document_name,
        "format_version": reloaded.format_version,
        "page_ids": [page.id for page in reloaded.pages],
        "item_ids": [item.id for item in reloaded.items],
        "note_titles": [note.title for note in reloaded.notes],
        "notes": [
            _note_summary(note_1_id, reloaded),
            _note_summary(note_2_id, reloaded),
        ],
        "lookup_demo": {
            "page_by_id": page_2_lookup.id,
            "note_by_id": note_2_lookup.title,
            "page_note_by_title": page_2_scoped_note.id,
        },
        "project_documents": project_documents,
        "manual_check": (
            "Open the generated project in Altium Designer, then open "
            f"{OUTPUT_DRAFTSMAN.name} and inspect both Draftsman pages."
        ),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    summary = build_draftsman_project()
    print(f"Wrote project to {summary['output_dir']}")
    print(f"Wrote {summary['output_draftsman']}")
    print(f"Page ids: {summary['page_ids']}")
    print(f"Wrote {_relative_to_examples(SUMMARY_PATH)}")


if __name__ == "__main__":
    main()
