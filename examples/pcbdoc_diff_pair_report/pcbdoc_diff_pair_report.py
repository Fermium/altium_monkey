from __future__ import annotations

import json
from pathlib import Path

from altium_monkey import AltiumDesign

SAMPLE_DIR = Path(__file__).resolve().parent
EXAMPLES_ROOT = SAMPLE_DIR.parent
PROJECT_DIR = EXAMPLES_ROOT / "assets" / "projects" / "rt_super_c1"
PROJECT_FILE = PROJECT_DIR / "RT_SUPER_C1.PrjPcb"
OUTPUT_DIR = SAMPLE_DIR / "output"
OUTPUT_JSON = OUTPUT_DIR / "pcbdoc_diff_pair_report.json"
OUTPUT_TEXT = OUTPUT_DIR / "pcbdoc_diff_pair_report.txt"


def _examples_relative(path: Path) -> str:
    return path.relative_to(EXAMPLES_ROOT).as_posix()


def _pair_row(pair: object) -> dict[str, object]:
    return {
        "name": str(getattr(pair, "name", "")),
        "positive_net_name": str(getattr(pair, "positive_net_name", "")),
        "negative_net_name": str(getattr(pair, "negative_net_name", "")),
        "gather_control": bool(getattr(pair, "gather_control", False)),
        "unique_id": str(getattr(pair, "unique_id", "")),
    }


def _class_row(pcb_class: object) -> dict[str, object]:
    return {
        "name": str(getattr(pcb_class, "name", "")),
        "member_count": int(getattr(pcb_class, "member_count", 0) or 0),
        "members": [str(member) for member in getattr(pcb_class, "members", [])],
    }


def _make_report() -> dict[str, object]:
    design = AltiumDesign.from_prjpcb(PROJECT_FILE)
    pcbdoc = design.load_pcbdoc()
    pcbdoc_path = Path(getattr(pcbdoc, "filepath", PROJECT_DIR / "RT_SUPER_C1.PCBdoc"))

    pairs = [_pair_row(pair) for pair in pcbdoc.differential_pairs]
    classes = [_class_row(pcb_class) for pcb_class in pcbdoc.differential_pair_classes]
    by_net = {
        net_name: pair.name
        for net_name, pair in sorted(pcbdoc.differential_pairs_by_net_name.items())
    }

    return {
        "project": _examples_relative(PROJECT_FILE),
        "pcbdoc": _examples_relative(pcbdoc_path),
        "differential_pair_count": len(pairs),
        "differential_pair_class_count": len(classes),
        "pairs": pairs,
        "classes": classes,
        "pair_by_net_name": by_net,
    }


def _table_lines(report: dict[str, object]) -> list[str]:
    pairs = [item for item in report["pairs"] if isinstance(item, dict)]
    lines = [
        f"Loaded project: {report['project']}",
        f"Loaded PCB: {report['pcbdoc']}",
        "",
        "Differential Pairs",
    ]
    if not pairs:
        lines.append("  (no differential pairs found)")
        return lines

    headers = ("name", "positive", "negative", "gather")
    rows = [
        (
            str(pair["name"]),
            str(pair["positive_net_name"]),
            str(pair["negative_net_name"]),
            "true" if pair["gather_control"] else "false",
        )
        for pair in pairs
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    lines.extend(
        [
            "  "
            + "  ".join(
                header.ljust(width)
                for header, width in zip(headers, widths, strict=True)
            ),
            "  " + "  ".join("-" * width for width in widths),
        ]
    )
    for row in rows:
        lines.append(
            "  "
            + "  ".join(
                value.ljust(width) for value, width in zip(row, widths, strict=True)
            )
        )

    classes = [item for item in report["classes"] if isinstance(item, dict)]
    lines.extend(["", "Differential Pair Classes"])
    if not classes:
        lines.append("  (no differential-pair classes found)")
    else:
        for pcb_class in classes:
            members = ", ".join(str(member) for member in pcb_class["members"])
            lines.append(
                f"  {pcb_class['name']}: "
                f"{pcb_class['member_count']} member(s)"
                + (f" [{members}]" if members else "")
            )
    return lines


def write_report() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = _make_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    OUTPUT_TEXT.write_text("\n".join(_table_lines(report)) + "\n", encoding="utf-8")
    return report


def main() -> None:
    report = write_report()
    for line in _table_lines(report):
        print(line)
    print()
    print(f"Wrote {OUTPUT_JSON.relative_to(SAMPLE_DIR)}")
    print(f"Wrote {OUTPUT_TEXT.relative_to(SAMPLE_DIR)}")


if __name__ == "__main__":
    main()
