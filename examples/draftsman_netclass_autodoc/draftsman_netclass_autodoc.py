from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from altium_monkey import AltiumDesign
from altium_monkey.altium_resolved_layer_stack import resolved_layer_stack_from_pcbdoc

from assembly_highlight import build_group_output, sample_relative
from autodoc_config import AutodocConfig


SAMPLE_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = SAMPLE_DIR.parent
CONFIG_DIR = SAMPLE_DIR / "configs"
OUTPUT_DIR = SAMPLE_DIR / "output"
OUTPUT_MANIFEST_FILENAME = "draftsman_netclass_autodoc_manifest.json"
DEFAULT_CONFIGS = (
    CONFIG_DIR / "bunny_brain.json",
    CONFIG_DIR / "rt_super_c1.json",
    CONFIG_DIR / "loz_old_man.json",
)


def _reset_output_dir() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _process_config(config_path: Path) -> dict[str, object]:
    config = AutodocConfig.from_json_file(config_path, examples_dir=EXAMPLES_DIR)
    output_dir = OUTPUT_DIR / config.output_name
    output_dir.mkdir(parents=True, exist_ok=True)

    design = AltiumDesign.from_prjpcb(config.source_project)
    pcbdoc = design.load_pcbdoc()
    stack = resolved_layer_stack_from_pcbdoc(pcbdoc)

    groups = [
        build_group_output(
            config=config,
            group=group,
            pcbdoc=pcbdoc,
            stack=stack,
            output_dir=output_dir,
        )
        for group in config.groups
    ]
    manifest = {
        "schema": config.schema,
        "config": sample_relative(config_path, sample_dir=SAMPLE_DIR),
        "project": sample_relative(config.source_project, sample_dir=EXAMPLES_DIR),
        "pcbdoc": sample_relative(
            Path(str(getattr(pcbdoc, "filepath", "") or "")),
            sample_dir=EXAMPLES_DIR,
        ),
        "output_dir": sample_relative(output_dir, sample_dir=SAMPLE_DIR),
        "sheet_size": config.sheet_size.display_name,
        "default_view_scale": config.view_scale,
        "auto_fit_scale": config.auto_fit_scale,
        "minimum_routing_length_mils": config.minimum_routing_length_mils,
        "connected_highlight_filter": config.connected_highlight_filter,
        "group_count": len(groups),
        "groups": [
            {
                "id": group.group_id,
                "title": group.title,
                "output_stem": group.output_stem,
                "draftsman_pcb_dwf": sample_relative(
                    group.draftsman_pcb_dwf,
                    sample_dir=SAMPLE_DIR,
                ),
                "draftsman_cache_xml": sample_relative(
                    group.draftsman_cache_xml,
                    sample_dir=SAMPLE_DIR,
                ),
                "effective_scale": group.effective_scale,
                "minimum_routing_length_mils": group.minimum_routing_length_mils,
                "connected_highlight_filter": group.connected_highlight_filter,
                "layers": group.layers,
            }
            for group in groups
        ],
    }
    manifest_path = output_dir / OUTPUT_MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        **manifest,
        "manifest": sample_relative(manifest_path, sample_dir=SAMPLE_DIR),
    }


def run(config_paths: tuple[Path, ...] = DEFAULT_CONFIGS) -> dict[str, object]:
    _reset_output_dir()
    project_manifests = [_process_config(path) for path in config_paths]
    manifest = {
        "schema": "altium-monkey.draftsman-netclass-autodoc.run.v1",
        "output_dir": sample_relative(OUTPUT_DIR, sample_dir=SAMPLE_DIR),
        "config_count": len(project_manifests),
        "projects": project_manifests,
    }
    manifest_path = OUTPUT_DIR / OUTPUT_MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        **manifest,
        "manifest": sample_relative(manifest_path, sample_dir=SAMPLE_DIR),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate grouped Draftsman board-assembly-view highlight pages "
            "from JSON netclass/differential-pair config files."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        action="append",
        default=None,
        help="JSON config to process. Can be provided more than once.",
    )
    args = parser.parse_args(argv)

    manifest = run(config_paths=tuple(args.config or DEFAULT_CONFIGS))
    print(f"Wrote output: {manifest['output_dir']}")
    print(f"Processed configs: {manifest['config_count']}")
    for project in manifest["projects"]:
        print(f"Loaded project: {project['project']}")
        print(f"  Config: {project['config']}")
        print(f"  Groups: {project['group_count']}")
        for group in project["groups"]:
            layer_names = ", ".join(
                str(layer["display_name"]) for layer in group["layers"]
            )
            print(
                f"    {group['title']}: {layer_names} "
                f"(scale {group['effective_scale']:.3g})"
            )
        print(f"  Wrote manifest: {project['manifest']}")
    print(f"Wrote aggregate manifest: {manifest['manifest']}")


if __name__ == "__main__":
    main()
