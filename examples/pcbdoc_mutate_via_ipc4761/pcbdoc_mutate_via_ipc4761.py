from __future__ import annotations

import json
import shutil
from pathlib import Path

from altium_monkey import (
    AltiumPcbDoc,
    AltiumPcbVia,
    PcbIpc4761ViaType,
    PcbViaStructureFeatureSide,
    PcbViaStructureFeatureType,
)

SAMPLE_DIR = Path(__file__).resolve().parent
EXAMPLES_ROOT = SAMPLE_DIR.parent
PROJECT_SOURCE_DIR = EXAMPLES_ROOT / "assets" / "projects" / "rt_super_c1"
OUTPUT_DIR = SAMPLE_DIR / "output"
WORK_PROJECT_DIR = OUTPUT_DIR / "rt_super_c1_type7_filled_vias"
WORK_PCBDOC = WORK_PROJECT_DIR / "RT_SUPER_C1.PCBdoc"
SUMMARY_PATH = OUTPUT_DIR / "mutation_summary.json"

IU_PER_MIL = 10000
TARGET_DIAMETER_MILS = 12.0
TARGET_HOLE_MILS = 6.0


def _mils(value: float) -> int:
    return int(round(value * IU_PER_MIL))


def _copy_project_to_output() -> None:
    if WORK_PROJECT_DIR.exists():
        shutil.rmtree(WORK_PROJECT_DIR)
    shutil.copytree(PROJECT_SOURCE_DIR, WORK_PROJECT_DIR)


def _matches_target_via(via: AltiumPcbVia) -> bool:
    return int(getattr(via, "diameter", 0) or 0) == _mils(TARGET_DIAMETER_MILS) and int(
        getattr(via, "hole_size", 0) or 0
    ) == _mils(TARGET_HOLE_MILS)


def _apply_type7_epoxy_fill(via: AltiumPcbVia) -> None:
    via.ipc4761_via_type = PcbIpc4761ViaType.TYPE_7_FILLING_AND_CAPPING
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


def mutate_project() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _copy_project_to_output()

    pcbdoc = AltiumPcbDoc.from_file(WORK_PCBDOC)
    matching_indices: list[int] = []
    for index, via in enumerate(pcbdoc.vias):
        if not _matches_target_via(via):
            continue
        matching_indices.append(index)
        _apply_type7_epoxy_fill(via)

    pcbdoc.save(WORK_PCBDOC)

    summary = {
        "source_project": "examples/assets/projects/rt_super_c1/RT_SUPER_C1.PrjPcb",
        "output_project": "examples/pcbdoc_mutate_via_ipc4761/output/rt_super_c1_type7_filled_vias/RT_SUPER_C1.PrjPcb",
        "output_pcbdoc": "examples/pcbdoc_mutate_via_ipc4761/output/rt_super_c1_type7_filled_vias/RT_SUPER_C1.PCBdoc",
        "target": {
            "diameter_mils": TARGET_DIAMETER_MILS,
            "hole_size_mils": TARGET_HOLE_MILS,
            "ipc4761_via_type": int(PcbIpc4761ViaType.TYPE_7_FILLING_AND_CAPPING),
            "intent": "epoxy-filled and capped/plated via representation",
        },
        "matched_via_count": len(matching_indices),
        "matched_via_indices": matching_indices,
        "total_via_count": len(pcbdoc.vias),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    summary = mutate_project()
    print(f"Copied project to {WORK_PROJECT_DIR}")
    print(f"Mutated {summary['matched_via_count']} vias")
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
