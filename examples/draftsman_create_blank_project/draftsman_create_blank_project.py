from __future__ import annotations

import json
import shutil
from pathlib import Path

from altium_monkey import AltiumDraftsmanDocument
from altium_monkey.altium_prjpcb import AltiumPrjPcb


SAMPLE_DIR = Path(__file__).resolve().parent
EXAMPLES_ROOT = SAMPLE_DIR.parent
PROJECT_SOURCE_DIR = EXAMPLES_ROOT / "assets" / "projects" / "rt_super_c1"

OUTPUT_DIR = SAMPLE_DIR / "output"
WORK_PROJECT_DIR = OUTPUT_DIR / "RT_SUPER_C1_BLANK_DRAFTSMAN"
WORK_PROJECT = WORK_PROJECT_DIR / "RT_SUPER_C1.PrjPcb"
WORK_PCBDOC = WORK_PROJECT_DIR / "RT_SUPER_C1.PCBdoc"
OUTPUT_DRAFTSMAN = WORK_PROJECT_DIR / "RT_SUPER_C1_Blank.PCBDwf"
SUMMARY_PATH = OUTPUT_DIR / "draftsman_create_blank_project.json"


def _relative_to_examples(path: Path) -> str:
    return path.resolve().relative_to(EXAMPLES_ROOT.resolve()).as_posix()


def _copy_project_to_output() -> None:
    shutil.copytree(PROJECT_SOURCE_DIR, WORK_PROJECT_DIR)


def _reset_output_dir() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_draftsman_project() -> dict[str, object]:
    _reset_output_dir()
    _copy_project_to_output()

    document = AltiumDraftsmanDocument.blank(
        profile="ad25",
        source_document_name=WORK_PCBDOC.name,
    )
    document.save(OUTPUT_DRAFTSMAN)

    project = AltiumPrjPcb(WORK_PROJECT)
    project.add_document(OUTPUT_DRAFTSMAN.name)
    project.save(WORK_PROJECT)

    reloaded = AltiumDraftsmanDocument.from_file(OUTPUT_DRAFTSMAN)
    reloaded_project = AltiumPrjPcb(WORK_PROJECT)
    project_documents = [
        str(document["path"]) for document in reloaded_project.documents
    ]
    summary = {
        "source_project": _relative_to_examples(PROJECT_SOURCE_DIR),
        "output_project_dir": _relative_to_examples(WORK_PROJECT_DIR),
        "output_prjpcb": _relative_to_examples(WORK_PROJECT),
        "output_pcbdoc": _relative_to_examples(WORK_PCBDOC),
        "output_draftsman": _relative_to_examples(OUTPUT_DRAFTSMAN),
        "blank_profile": "ad25",
        "source_document_name": reloaded.source_document_name,
        "format_version": reloaded.format_version,
        "is_blank_drawing": len(reloaded.items) == 0,
        "page_count": len(reloaded.pages),
        "item_count": len(reloaded.items),
        "note_count": len(reloaded.notes),
        "text_count": len(reloaded.texts),
        "picture_count": len(reloaded.pictures),
        "project_documents": project_documents,
        "manual_check": (
            "Open the copied project in Altium Designer, then open the generated "
            "RT_SUPER_C1_Blank.PCBDwf file."
        ),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    summary = build_draftsman_project()
    print(f"Copied project to {summary['output_project_dir']}")
    print(f"Wrote {summary['output_draftsman']}")
    print(f"Blank drawing items: {summary['item_count']}")
    print(f"Wrote {_relative_to_examples(SUMMARY_PATH)}")


if __name__ == "__main__":
    main()
