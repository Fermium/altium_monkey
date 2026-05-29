from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

from altium_monkey import DraftsmanStandardSheetSize, PcbLayer


SCHEMA = "altium-monkey.draftsman-netclass-autodoc.v1"
DEFAULT_CONTEXT_COPPER = "#B8B8B8"
DEFAULT_HIGHLIGHT = "#D00000"
DEFAULT_PAD_COPPER = "#000000"
DEFAULT_DRILL_HOLE = "#FFFFFF"
DEFAULT_NON_PLATED_HOLE = "#808080"
DEFAULT_GRID = "#BEBEBE"


@dataclass(frozen=True)
class BucketOptions:
    context_topology: bool = True
    context_smd_pads: bool = True
    context_through_hole_pads: bool = True
    context_via_pads: bool = True
    drill_holes: bool = True
    highlighted_pads_and_vias: bool = True

    @classmethod
    def from_json(cls, value: object | None) -> "BucketOptions":
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("buckets must be a JSON object")
        return cls(
            context_topology=_bool_field(value, "context_topology", True),
            context_smd_pads=_bool_field(value, "context_smd_pads", True),
            context_through_hole_pads=_bool_field(
                value,
                "context_through_hole_pads",
                True,
            ),
            context_via_pads=_bool_field(value, "context_via_pads", True),
            drill_holes=_bool_field(value, "drill_holes", True),
            highlighted_pads_and_vias=_bool_field(
                value,
                "highlighted_pads_and_vias",
                True,
            ),
        )


@dataclass(frozen=True)
class AutodocStyle:
    highlight_copper: str = DEFAULT_HIGHLIGHT
    context_copper: str = DEFAULT_CONTEXT_COPPER
    smd_pad_copper: str = DEFAULT_PAD_COPPER
    through_hole_pad_copper: str = DEFAULT_PAD_COPPER
    via_pad_copper: str = DEFAULT_PAD_COPPER
    drill_hole: str = DEFAULT_DRILL_HOLE
    non_plated_hole: str = DEFAULT_NON_PLATED_HOLE
    document_grid: str = DEFAULT_GRID

    @classmethod
    def from_json(
        cls,
        value: object | None,
        *,
        base: "AutodocStyle | None" = None,
    ) -> "AutodocStyle":
        style = base or cls()
        if value is None:
            return style
        if not isinstance(value, dict):
            raise ValueError("style must be a JSON object")
        return replace(
            style,
            highlight_copper=_color_field(
                value,
                "highlight_copper",
                _color_field(value, "highlight_color", style.highlight_copper),
            ),
            context_copper=_color_field(value, "context_copper", style.context_copper),
            smd_pad_copper=_color_field(
                value,
                "smd_pad_copper",
                _color_field(value, "pad_via_copper", style.smd_pad_copper),
            ),
            through_hole_pad_copper=_color_field(
                value,
                "through_hole_pad_copper",
                _color_field(value, "pad_via_copper", style.through_hole_pad_copper),
            ),
            via_pad_copper=_color_field(
                value,
                "via_pad_copper",
                _color_field(value, "pad_via_copper", style.via_pad_copper),
            ),
            drill_hole=_color_field(
                value,
                "drill_hole",
                _color_field(value, "hole", style.drill_hole),
            ),
            non_plated_hole=_color_field(
                value,
                "non_plated_hole",
                _color_field(
                    value,
                    "non_plated_drill_hole",
                    _color_field(value, "npth_hole", style.non_plated_hole),
                ),
            ),
            document_grid=_color_field(value, "document_grid", style.document_grid),
        )


@dataclass(frozen=True)
class AutodocGroup:
    id: str
    title: str
    notes: tuple[str, ...]
    net_classes: tuple[str, ...]
    differential_pair_classes: tuple[str, ...]
    differential_pairs: tuple[str, ...]
    nets: tuple[str, ...]
    layers: tuple[PcbLayer, ...] | None
    view_scale: float | None
    target_fill_ratio: float | None
    tile_gap_x_mm: float | None
    tile_gap_y_mm: float | None
    minimum_routing_length_mils: float | None
    connected_highlight_filter: bool | None
    auto_fit_scale: bool
    style: AutodocStyle
    buckets: BucketOptions

    @classmethod
    def from_json(
        cls,
        value: object,
        *,
        default_style: AutodocStyle,
        default_auto_fit_scale: bool,
    ) -> "AutodocGroup":
        if not isinstance(value, dict):
            raise ValueError("each group must be a JSON object")
        group_id = _required_string(value, "id")
        style = AutodocStyle.from_json(value.get("style"), base=default_style)
        if "highlight_color" in value:
            style = replace(
                style,
                highlight_copper=_color_field(
                    value,
                    "highlight_color",
                    style.highlight_copper,
                ),
            )
        title = _string_field(value, "title", group_id)
        group = cls(
            id=group_id,
            title=title,
            notes=_string_tuple(value.get("notes")),
            net_classes=_string_tuple(value.get("net_classes")),
            differential_pair_classes=_string_tuple(
                value.get("differential_pair_classes")
            ),
            differential_pairs=_string_tuple(value.get("differential_pairs")),
            nets=_string_tuple(value.get("nets")),
            layers=_layers_or_none(value.get("layers")),
            view_scale=_optional_float(value.get("view_scale"), "view_scale"),
            target_fill_ratio=_optional_ratio(value.get("target_fill_ratio")),
            tile_gap_x_mm=_optional_float(value.get("tile_gap_x_mm"), "tile_gap_x_mm"),
            tile_gap_y_mm=_optional_float(value.get("tile_gap_y_mm"), "tile_gap_y_mm"),
            minimum_routing_length_mils=_optional_non_negative_float(
                value.get("minimum_routing_length_mils"),
                "minimum_routing_length_mils",
            ),
            connected_highlight_filter=_optional_bool_field(
                value,
                "connected_highlight_filter",
            ),
            auto_fit_scale=_bool_field(
                value,
                "auto_fit_scale",
                default_auto_fit_scale,
            ),
            style=style,
            buckets=BucketOptions.from_json(value.get("buckets")),
        )
        if not (
            group.net_classes
            or group.differential_pair_classes
            or group.differential_pairs
            or group.nets
        ):
            raise ValueError(f"group {group.id!r} has no selectors")
        return group


@dataclass(frozen=True)
class AutodocConfig:
    schema: str
    source_project: Path
    output_name: str
    sheet_size: DraftsmanStandardSheetSize
    view_scale: float
    target_fill_ratio: float
    tile_gap_x_mm: float
    tile_gap_y_mm: float
    auto_fit_scale: bool
    minimum_routing_length_mils: float
    connected_highlight_filter: bool
    style: AutodocStyle
    groups: tuple[AutodocGroup, ...]

    @classmethod
    def from_json_file(
        cls,
        path: Path,
        *,
        examples_dir: Path,
    ) -> "AutodocConfig":
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"{path} must contain a JSON object")
        schema = _string_field(value, "schema", SCHEMA)
        source_project = _resolve_project_path(
            _required_string(value, "source_project"),
            examples_dir=examples_dir,
            config_path=path,
        )
        output_name = _string_field(value, "output_name", _safe_filename(path.stem))
        style = AutodocStyle.from_json(value.get("style"))
        auto_fit_scale = _bool_field(value, "auto_fit_scale", True)
        groups = tuple(
            AutodocGroup.from_json(
                group,
                default_style=style,
                default_auto_fit_scale=auto_fit_scale,
            )
            for group in _list_field(value, "groups")
        )
        if not groups:
            raise ValueError(f"{path} must define at least one group")
        return cls(
            schema=schema,
            source_project=source_project,
            output_name=output_name,
            sheet_size=_sheet_size(value.get("sheet_size", "ANSI B")),
            view_scale=_float_field(value, "view_scale", 1.0),
            target_fill_ratio=_ratio_field(value, "target_fill_ratio", 0.75),
            tile_gap_x_mm=_float_field(value, "tile_gap_x_mm", 8.0),
            tile_gap_y_mm=_float_field(value, "tile_gap_y_mm", 8.0),
            auto_fit_scale=auto_fit_scale,
            minimum_routing_length_mils=_non_negative_float_field(
                value,
                "minimum_routing_length_mils",
                10.0,
            ),
            connected_highlight_filter=_bool_field(
                value,
                "connected_highlight_filter",
                True,
            ),
            style=style,
            groups=groups,
        )


def _safe_filename(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return token.strip("_").lower() or "item"


def _resolve_project_path(
    value: str,
    *,
    examples_dir: Path,
    config_path: Path,
) -> Path:
    source_path = Path(value)
    if source_path.is_absolute():
        return source_path
    examples_candidate = (examples_dir / source_path).resolve()
    if examples_candidate.exists():
        return examples_candidate
    return (config_path.parent / source_path).resolve()


def _required_string(value: dict[str, object], key: str) -> str:
    result = _string_field(value, key, "")
    if not result:
        raise ValueError(f"missing required string field {key!r}")
    return result


def _string_field(value: dict[str, object], key: str, default: str) -> str:
    raw = value.get(key, default)
    if raw is None:
        return default
    return str(raw).strip()


def _string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list):
        raise ValueError("expected a string array")
    return tuple(str(item).strip() for item in value if str(item).strip())


def _list_field(value: dict[str, object], key: str) -> list[object]:
    raw = value.get(key, [])
    if not isinstance(raw, list):
        raise ValueError(f"{key!r} must be an array")
    return raw


def _bool_field(value: dict[str, object], key: str, default: bool) -> bool:
    raw = value.get(key, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip().casefold()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return bool(raw)


def _optional_bool_field(value: dict[str, object], key: str) -> bool | None:
    if key not in value or value[key] is None:
        return None
    return _bool_field(value, key, False)


def _float_field(value: dict[str, object], key: str, default: float) -> float:
    raw = value.get(key, default)
    return _float_value(raw, key)


def _non_negative_float_field(
    value: dict[str, object],
    key: str,
    default: float,
) -> float:
    raw = value.get(key, default)
    return _non_negative_float_value(raw, key)


def _ratio_field(value: dict[str, object], key: str, default: float) -> float:
    result = _float_field(value, key, default)
    if result > 1.0:
        raise ValueError(f"{key!r} must be less than or equal to one")
    return result


def _optional_float(value: object | None, key: str) -> float | None:
    if value is None:
        return None
    return _float_value(value, key)


def _optional_non_negative_float(value: object | None, key: str) -> float | None:
    if value is None:
        return None
    return _non_negative_float_value(value, key)


def _optional_ratio(value: object | None) -> float | None:
    if value is None:
        return None
    result = _float_value(value, "target_fill_ratio")
    if result > 1.0:
        raise ValueError("'target_fill_ratio' must be less than or equal to one")
    return result


def _float_value(value: object, key: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key!r} must be a number") from exc
    if result <= 0.0:
        raise ValueError(f"{key!r} must be greater than zero")
    return result


def _non_negative_float_value(value: object, key: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key!r} must be a number") from exc
    if result < 0.0:
        raise ValueError(f"{key!r} must be greater than or equal to zero")
    return result


def _color_field(value: dict[str, object], key: str, default: str) -> str:
    raw = value.get(key, default)
    color = str(raw or default).strip()
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise ValueError(f"{key!r} must be a #RRGGBB color")
    return color.upper()


def _sheet_size(value: object) -> DraftsmanStandardSheetSize:
    name = str(value or "").strip()
    result = DraftsmanStandardSheetSize.from_display_name(name)
    if result is not None:
        return result
    normalized = name.replace(" ", "_").replace("-", "_").upper()
    try:
        return DraftsmanStandardSheetSize[normalized]
    except KeyError as exc:
        raise ValueError(f"unknown sheet_size {name!r}") from exc


def _layers_or_none(value: object | None) -> tuple[PcbLayer, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("layers must be an array")
    layers: list[PcbLayer] = []
    for item in value:
        layer_id: object
        if isinstance(item, dict):
            layer_id = item.get("legacy_id", item.get("id"))
        else:
            layer_id = item
        if isinstance(layer_id, str) and not layer_id.strip().isdigit():
            layers.append(PcbLayer.from_json_name(layer_id))
        else:
            layers.append(PcbLayer(int(layer_id)))
    return tuple(dict.fromkeys(layers))
