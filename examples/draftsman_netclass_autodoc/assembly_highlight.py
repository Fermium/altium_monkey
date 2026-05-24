from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from lxml import etree

from altium_monkey import (
    AltiumDraftsmanDocument,
    DraftsmanColor,
    DraftsmanHorizontalAlignment,
    DraftsmanRect,
    DraftsmanVerticalAlignment,
    PcbLayer,
)
from altium_monkey.altium_draftsman import draftsman_points_from_mm
from altium_monkey.altium_draftsman_pcb_geometry_xml import (
    DraftsmanPcbCacheLayer,
    DraftsmanPcbCachePrimitive,
    DraftsmanPcbDisplayLayer,
    board_assembly_information_xml,
    board_assembly_view_item_xml,
    board_layers_geometry_information_xml,
    board_projection_information_xml,
    draftsman_color_from_hex_rgb,
    ensure_board_assembly_view_document_resources,
)
from altium_monkey.altium_draftsman_xml import (
    element_local_name,
    first_child_by_local_name,
    qualified_name,
)
from altium_monkey.altium_pcb_drawing_geometry import (
    PcbDrawingDocument,
    PcbDrawingArc,
    PcbDrawingPoint,
    PcbDrawingPrimitive,
    PcbDrawingUni,
    build_pcb_drawing_geometry,
)
from altium_monkey.altium_resolved_layer_stack import ResolvedLayerStack

from autodoc_config import AutodocConfig, AutodocGroup


PAGE_MARGIN_MM = 12.0
VIEW_GAP_MM = 8.0
TITLE_FONT_SIZE = 40.0
NOTE_FONT_SIZE = 12.0
TITLE_HEIGHT_MM = 22.0
NOTE_TOP_GAP_MM = 4.0
NOTE_ROW_HEIGHT_MM = 8.5
MIN_HEADER_HEIGHT_MM = 44.0
NOTE_WIDTH_MM = 320.0
MECHANICAL_BUCKET_LAYERS = (
    PcbLayer.MECHANICAL_1,
    PcbLayer.MECHANICAL_2,
    PcbLayer.MECHANICAL_3,
    PcbLayer.MECHANICAL_4,
    PcbLayer.MECHANICAL_5,
    PcbLayer.MECHANICAL_6,
    PcbLayer.MECHANICAL_7,
    PcbLayer.MECHANICAL_8,
    PcbLayer.MECHANICAL_9,
    PcbLayer.MECHANICAL_10,
    PcbLayer.MECHANICAL_11,
    PcbLayer.MECHANICAL_12,
    PcbLayer.MECHANICAL_13,
    PcbLayer.MECHANICAL_14,
    PcbLayer.MECHANICAL_15,
    PcbLayer.MECHANICAL_16,
)
GEOMETRY_TOUCH_TOLERANCE_MILS = 1.0


@dataclass(frozen=True)
class LayerViewPlan:
    layer: PcbLayer
    layer_name: str
    cache_layers: tuple[DraftsmanPcbCacheLayer, ...]
    display_layers: tuple[DraftsmanPcbDisplayLayer, ...]
    selected_copper: tuple[PcbDrawingPrimitive, ...]
    context_topology: tuple[PcbDrawingPrimitive, ...]
    context_smd_pads: tuple[PcbDrawingPrimitive, ...]
    context_through_hole_pads: tuple[PcbDrawingPrimitive, ...]
    context_via_pads: tuple[PcbDrawingPrimitive, ...]
    drill_holes: tuple[PcbDrawingPrimitive, ...]
    plated_drill_holes: tuple[PcbDrawingPrimitive, ...]
    non_plated_drill_holes: tuple[PcbDrawingPrimitive, ...]
    show_topology: bool
    show_mask: bool
    source_layer_visible: bool
    highlight_color: DraftsmanColor
    context_color: DraftsmanColor
    smd_pad_color: DraftsmanColor
    through_hole_pad_color: DraftsmanColor
    via_pad_color: DraftsmanColor
    drill_hole_color: DraftsmanColor
    non_plated_hole_color: DraftsmanColor


@dataclass(frozen=True)
class LayerPlacement:
    plan: LayerViewPlan
    left_mm: float
    top_mm: float
    scale: float
    view_width_mm: float
    view_height_mm: float


@dataclass(frozen=True)
class GroupOutput:
    group_id: str
    title: str
    output_stem: str
    draftsman_pcb_dwf: Path
    draftsman_cache_xml: Path
    effective_scale: float
    minimum_routing_length_mils: float
    connected_highlight_filter: bool
    layers: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class RouteArtworkComponent:
    primitives: tuple[PcbDrawingPrimitive, ...]
    length_mils: float


class MechanicalBucketAllocator:
    def __init__(self) -> None:
        self._index = 0

    def allocate(self) -> PcbLayer:
        if self._index >= len(MECHANICAL_BUCKET_LAYERS):
            raise ValueError("not enough helper mechanical layers for this group")
        layer = MECHANICAL_BUCKET_LAYERS[self._index]
        self._index += 1
        return layer


def build_group_output(
    *,
    config: AutodocConfig,
    group: AutodocGroup,
    pcbdoc: object,
    stack: ResolvedLayerStack,
    output_dir: Path,
) -> GroupOutput:
    drawing = build_pcb_drawing_geometry(pcbdoc)
    layer_views = _layer_view_plans(
        config=config,
        group=group,
        drawing=drawing,
        stack=stack,
    )
    if not layer_views:
        raise ValueError(f"group {group.id!r} did not match routed PCB geometry")

    output_stem = _safe_filename(group.id)
    effective_scale, placements = _place_layer_views(
        config=config,
        group=group,
        pcbdoc=pcbdoc,
        layer_views=layer_views,
    )
    cache_layers = _merge_cache_layers(
        cache_layer
        for layer_view in layer_views
        for cache_layer in layer_view.cache_layers
    )
    cache_path = _write_cache_fragment(
        output_dir=output_dir,
        output_stem=output_stem,
        cache_layers=cache_layers,
    )
    draftsman_path = _write_draftsman_document(
        config=config,
        group=group,
        output_dir=output_dir,
        output_stem=output_stem,
        pcbdoc=pcbdoc,
        stack=stack,
        cache_layers=cache_layers,
        placements=placements,
        effective_scale=effective_scale,
    )
    return GroupOutput(
        group_id=group.id,
        title=group.title,
        output_stem=output_stem,
        draftsman_pcb_dwf=draftsman_path,
        draftsman_cache_xml=cache_path,
        effective_scale=effective_scale,
        minimum_routing_length_mils=_minimum_routing_length_mils(
            config=config,
            group=group,
        ),
        connected_highlight_filter=_connected_highlight_filter(
            config=config,
            group=group,
        ),
        layers=tuple(
            _layer_view_summary(
                plan=placement.plan,
                placement=placement,
                stack=stack,
            )
            for placement in placements
        ),
    )


def _layer_view_plans(
    *,
    config: AutodocConfig,
    group: AutodocGroup,
    drawing: PcbDrawingDocument,
    stack: ResolvedLayerStack,
) -> tuple[LayerViewPlan, ...]:
    minimum_routing_length_mils = _minimum_routing_length_mils(
        config=config,
        group=group,
    )
    connected_highlight_filter = _connected_highlight_filter(
        config=config,
        group=group,
    )
    layers = _sort_signal_layers(
        group.layers
        or _selected_layers(
            group=group,
            drawing=drawing,
            minimum_routing_length_mils=minimum_routing_length_mils,
            connected_highlight_filter=connected_highlight_filter,
        )
    )
    allocator = MechanicalBucketAllocator()
    plans: list[LayerViewPlan] = []
    for layer in layers:
        primitives = drawing.primitives_for_layer(layer)
        plan = _layer_view_plan(
            group=group,
            layer=layer,
            primitives=primitives,
            minimum_routing_length_mils=minimum_routing_length_mils,
            connected_highlight_filter=connected_highlight_filter,
            stack=stack,
            allocator=allocator,
        )
        if plan is not None:
            plans.append(plan)
    return tuple(plans)


def _selected_layers(
    *,
    group: AutodocGroup,
    drawing: PcbDrawingDocument,
    minimum_routing_length_mils: float,
    connected_highlight_filter: bool,
) -> tuple[PcbLayer, ...]:
    layers = {
        layer.layer
        for layer in drawing.layers
        if _highlighted_route_artwork(
            group=group,
            primitives=layer.primitives,
            minimum_routing_length_mils=minimum_routing_length_mils,
            connected_highlight_filter=connected_highlight_filter,
        )
    }
    return _sort_signal_layers(layers)


def _sort_signal_layers(layers: Iterable[PcbLayer]) -> tuple[PcbLayer, ...]:
    return tuple(sorted(dict.fromkeys(layers), key=_signal_layer_sort_key))


def _signal_layer_sort_key(layer: PcbLayer) -> tuple[int, int]:
    if layer == PcbLayer.TOP:
        return (0, layer.value)
    if layer == PcbLayer.BOTTOM:
        return (2, layer.value)
    if layer.is_copper():
        return (1, layer.value)
    return (3, layer.value)


def _layer_view_plan(
    *,
    group: AutodocGroup,
    layer: PcbLayer,
    primitives: tuple[PcbDrawingPrimitive, ...],
    minimum_routing_length_mils: float,
    connected_highlight_filter: bool,
    stack: ResolvedLayerStack,
    allocator: MechanicalBucketAllocator,
) -> LayerViewPlan | None:
    selected_artwork = _highlighted_route_artwork(
        group=group,
        primitives=primitives,
        minimum_routing_length_mils=minimum_routing_length_mils,
        connected_highlight_filter=connected_highlight_filter,
    )
    if not selected_artwork:
        return None

    selected_pad_vias = _selected_pad_vias(
        group=group,
        primitives=primitives,
        selected_artwork=selected_artwork,
        connected_highlight_filter=connected_highlight_filter,
    )
    through_hole_keys = _through_hole_pad_keys(primitives)
    external_layer = _is_external_signal_layer(layer)
    selected_copper = selected_artwork + selected_pad_vias
    selected_copper_ids = {id(primitive) for primitive in selected_copper}
    context = tuple(
        primitive
        for primitive in primitives
        if id(primitive) not in selected_copper_ids
    )
    context_copper = tuple(
        primitive for primitive in context if primitive.role == "copper"
    )
    context_topology = tuple(
        primitive
        for primitive in context_copper
        if group.buckets.context_topology and _is_topology_artwork_primitive(primitive)
    )
    context_smd_pads = tuple(
        primitive
        for primitive in context_copper
        if external_layer
        and group.buckets.context_smd_pads
        and _is_smd_component_pad(primitive, through_hole_keys)
    )
    context_through_hole_pads = tuple(
        primitive
        for primitive in context_copper
        if external_layer
        and group.buckets.context_through_hole_pads
        and _is_through_hole_component_pad(primitive, through_hole_keys)
    )
    context_via_pads = tuple(
        primitive
        for primitive in context_copper
        if group.buckets.context_via_pads and primitive.primitive_kind == "via"
    )
    drill_holes = tuple(
        primitive
        for primitive in primitives
        if group.buckets.drill_holes and _is_drill_hole_primitive(primitive)
    )
    non_plated_drill_holes = tuple(
        primitive for primitive in drill_holes if primitive.is_plated is False
    )
    plated_drill_holes = tuple(
        primitive for primitive in drill_holes if primitive.is_plated is not False
    )
    colors = _style_colors(group)
    highlight_layer = _highlight_layer_for_view(layer, allocator)
    show_mask = highlight_layer in {PcbLayer.TOP_SOLDER, PcbLayer.BOTTOM_SOLDER}
    show_topology = layer in {PcbLayer.TOP, PcbLayer.BOTTOM} and bool(context_topology)
    source_layer_visible = bool(context_topology) and not show_topology
    drill_display_layers: list[DraftsmanPcbDisplayLayer] = []
    selected_route_display_layers: list[DraftsmanPcbDisplayLayer] = []
    selected_pad_display_layers: list[DraftsmanPcbDisplayLayer] = []
    context_pad_display_layers: list[DraftsmanPcbDisplayLayer] = []
    cache_layers: list[DraftsmanPcbCacheLayer] = []
    layer_name = _layer_display_name(layer, stack)

    if context_topology:
        cache_layers.append(
            DraftsmanPcbCacheLayer(
                layer=layer,
                primitives=_draftsman_bucket_primitives(context_topology),
                name=layer_name,
                color=colors["context"],
                thickness_mils=_layer_thickness_mils(layer, stack),
            )
        )
    selected_route_bucket = selected_copper if show_mask else selected_artwork
    if selected_route_bucket:
        cache_layers.append(
            DraftsmanPcbCacheLayer(
                layer=highlight_layer,
                primitives=_draftsman_bucket_primitives(selected_route_bucket),
                name=f"{layer_name} Highlight",
                color=colors["highlight"],
                thickness_mils=_layer_thickness_mils(highlight_layer, stack),
            )
        )
        if not show_mask:
            selected_route_display_layers.append(
                DraftsmanPcbDisplayLayer(
                    layer=highlight_layer,
                    color=colors["highlight"],
                )
            )

    if selected_pad_vias and not show_mask:
        selected_pad_display_layers.extend(
            _helper_layer(
                allocator=allocator,
                cache_layers=cache_layers,
                primitives=selected_pad_vias,
                layer_name=f"{layer_name} Highlight Pads and Vias",
                color=colors["highlight"],
            )
        )

    context_pad_display_layers.extend(
        _context_pad_helper_layers(
            allocator=allocator,
            cache_layers=cache_layers,
            layer_name=layer_name,
            context_smd_pads=context_smd_pads,
            context_through_hole_pads=context_through_hole_pads,
            context_via_pads=context_via_pads,
            colors=colors,
        )
    )
    if plated_drill_holes:
        drill_display_layers.extend(
            _helper_layer(
                allocator=allocator,
                cache_layers=cache_layers,
                primitives=plated_drill_holes,
                layer_name=f"{layer_name} Drill Hole Overlay",
                color=colors["drill_hole"],
                force_copper=True,
            )
        )
    if non_plated_drill_holes:
        drill_display_layers.extend(
            _helper_layer(
                allocator=allocator,
                cache_layers=cache_layers,
                primitives=non_plated_drill_holes,
                layer_name=f"{layer_name} Non-Plated Hole Overlay",
                color=colors["non_plated_hole"],
                force_copper=True,
            )
        )
    if drill_holes:
        paste_layer = _paste_layer_for_view(layer)
        cache_layers.append(
            DraftsmanPcbCacheLayer(
                layer=paste_layer,
                primitives=_draftsman_bucket_primitives(
                    tuple(
                        _as_copper_primitive(primitive, layer=paste_layer)
                        for primitive in drill_holes
                    )
                ),
                name=f"{layer_name} Drill Holes",
                color=colors["drill_hole"],
                thickness_mils=_layer_thickness_mils(paste_layer, stack),
            )
        )

    return LayerViewPlan(
        layer=layer,
        layer_name=layer_name,
        cache_layers=tuple(cache_layers),
        # Draftsman renders the first showed helper layer on top.
        display_layers=tuple(
            drill_display_layers
            + selected_pad_display_layers
            + context_pad_display_layers
            + selected_route_display_layers
        ),
        selected_copper=selected_copper,
        context_topology=context_topology,
        context_smd_pads=context_smd_pads,
        context_through_hole_pads=context_through_hole_pads,
        context_via_pads=context_via_pads,
        drill_holes=drill_holes,
        plated_drill_holes=plated_drill_holes,
        non_plated_drill_holes=non_plated_drill_holes,
        show_topology=show_topology,
        show_mask=show_mask,
        source_layer_visible=source_layer_visible,
        highlight_color=colors["highlight"],
        context_color=colors["context"],
        smd_pad_color=colors["smd_pad"],
        through_hole_pad_color=colors["through_hole_pad"],
        via_pad_color=colors["via_pad"],
        drill_hole_color=colors["drill_hole"],
        non_plated_hole_color=colors["non_plated_hole"],
    )


def _context_pad_helper_layers(
    *,
    allocator: MechanicalBucketAllocator,
    cache_layers: list[DraftsmanPcbCacheLayer],
    layer_name: str,
    context_smd_pads: tuple[PcbDrawingPrimitive, ...],
    context_through_hole_pads: tuple[PcbDrawingPrimitive, ...],
    context_via_pads: tuple[PcbDrawingPrimitive, ...],
    colors: dict[str, DraftsmanColor],
) -> tuple[DraftsmanPcbDisplayLayer, ...]:
    pad_groups = tuple(
        group
        for group in (
            (context_smd_pads, f"{layer_name} SMD Pads", colors["smd_pad"]),
            (
                context_through_hole_pads,
                f"{layer_name} Through-Hole Pads",
                colors["through_hole_pad"],
            ),
            (context_via_pads, f"{layer_name} Via Pads", colors["via_pad"]),
        )
        if group[0]
    )
    if not pad_groups:
        return ()

    first_color = pad_groups[0][2]
    if all(group[2] == first_color for group in pad_groups):
        primitives: list[PcbDrawingPrimitive] = []
        for group_primitives, _, _ in pad_groups:
            primitives.extend(group_primitives)
        return _helper_layer(
            allocator=allocator,
            cache_layers=cache_layers,
            primitives=tuple(primitives),
            layer_name=f"{layer_name} Pads and Vias",
            color=first_color,
        )

    display_layers: list[DraftsmanPcbDisplayLayer] = []
    for primitives, helper_name, color in pad_groups:
        display_layers.extend(
            _helper_layer(
                allocator=allocator,
                cache_layers=cache_layers,
                primitives=primitives,
                layer_name=helper_name,
                color=color,
            )
        )
    return tuple(display_layers)


def _helper_layer(
    *,
    allocator: MechanicalBucketAllocator,
    cache_layers: list[DraftsmanPcbCacheLayer],
    primitives: tuple[PcbDrawingPrimitive, ...],
    layer_name: str,
    color: DraftsmanColor,
    force_copper: bool = False,
) -> tuple[DraftsmanPcbDisplayLayer, ...]:
    layer = allocator.allocate()
    helper_primitives = (
        tuple(_as_copper_primitive(primitive, layer=layer) for primitive in primitives)
        if force_copper
        else primitives
    )
    cache_layers.append(
        DraftsmanPcbCacheLayer(
            layer=layer,
            primitives=_draftsman_bucket_primitives(helper_primitives),
            name=layer_name,
            color=color,
        )
    )
    return (DraftsmanPcbDisplayLayer(layer=layer, color=color),)


def _write_draftsman_document(
    *,
    config: AutodocConfig,
    group: AutodocGroup,
    output_dir: Path,
    output_stem: str,
    pcbdoc: object,
    stack: ResolvedLayerStack,
    cache_layers: tuple[DraftsmanPcbCacheLayer, ...],
    placements: tuple[LayerPlacement, ...],
    effective_scale: float,
) -> Path:
    pcbdoc_path = Path(str(getattr(pcbdoc, "filepath", "") or "source.PcbDoc"))
    document = AltiumDraftsmanDocument.blank(
        profile="ad25",
        source_document_name=pcbdoc_path.name,
    )
    page = document.pages[0]
    page.apply_standard_sheet_size(config.sheet_size)
    document.document_options.grid_color = draftsman_color_from_hex_rgb(
        group.style.document_grid
    )
    resources = ensure_board_assembly_view_document_resources(document)
    title_font = document.get_or_create_font_style("Arial", TITLE_FONT_SIZE, bold=True)
    note_font = document.get_or_create_font_style("Arial", NOTE_FONT_SIZE)

    _replace_document_child(
        document,
        board_assembly_information_xml(
            pcbdoc,
            board_thickness_mils=_board_thickness_mils(stack),
        ),
    )
    _replace_document_child(
        document,
        board_layers_geometry_information_xml(cache_layers),
    )
    _replace_document_child(document, board_projection_information_xml(pcbdoc))
    _add_page_header(page=page, group=group, title_font=title_font, note_font=note_font)

    for placement in placements:
        plan = placement.plan
        view_item = board_assembly_view_item_xml(
            item_id=document.next_page_or_item_id,
            board_source_name=str(pcbdoc_path),
            layer=plan.layer,
            layer_color=plan.context_color,
            location_x_points=draftsman_points_from_mm(placement.left_mm),
            location_y_points=draftsman_points_from_mm(placement.top_mm),
            title=f"{group.title} - {plan.layer_name}",
            title_font_style_id=resources.title_font_style_id,
            component_font_style_id=resources.component_font_style_id,
            board_shape_line_style_id=resources.board_shape_line_style_id,
            component_line_style_id=resources.component_line_style_id,
            component_fill_style_id=resources.component_fill_style_id,
            showed_layer_visible=plan.source_layer_visible,
            extra_showed_layers=plan.display_layers,
            mask_color=plan.highlight_color,
            show_mask=plan.show_mask,
            paste_color=plan.drill_hole_color,
            show_paste=bool(plan.drill_holes),
            smd_pads_color=plan.smd_pad_color,
            show_smd_pads=bool(plan.context_smd_pads),
            through_hole_pads_color=plan.through_hole_pad_color,
            show_through_hole_pads=bool(plan.context_through_hole_pads),
            show_topology=plan.show_topology,
            scale_numenator=effective_scale,
            scale_denominator=1.0,
            primary_showed_layer_first=not plan.source_layer_visible,
        )
        _append_page_item(page, view_item)

    output_path = output_dir / f"{output_stem}.PCBDwf"
    document.save(output_path, compression="raw", pretty_print=True)
    AltiumDraftsmanDocument.from_file(output_path)
    return output_path


def _add_page_header(
    *,
    page: object,
    group: AutodocGroup,
    title_font: object,
    note_font: object,
) -> None:
    size = page.size
    if size is None:
        raise ValueError("Draftsman page size is not available")
    available_width = size.width_mm - PAGE_MARGIN_MM * 2.0
    page.add_text(
        text=group.title,
        rect=_rect_from_top_left(
            page,
            left_mm=PAGE_MARGIN_MM,
            top_mm=PAGE_MARGIN_MM,
            width_mm=available_width,
            height_mm=TITLE_HEIGHT_MM,
        ),
        font_style=title_font,
        color=DraftsmanColor.rgb(0, 0, 0),
        horizontal_alignment=DraftsmanHorizontalAlignment.LEFT,
        vertical_alignment=DraftsmanVerticalAlignment.CENTER,
    )
    if group.notes:
        notes_width = min(NOTE_WIDTH_MM, available_width)
        point = page.point_from_top_left(
            left_mm=PAGE_MARGIN_MM,
            top_mm=PAGE_MARGIN_MM + TITLE_HEIGHT_MM + NOTE_TOP_GAP_MM,
        )
        page.add_note(
            title="Notes",
            rect=DraftsmanRect(
                x_mm=point.x_mm,
                y_mm=point.y_mm,
                width_mm=notes_width,
                height_mm=0.0,
            ),
            bullets=group.notes,
            element_font_style=note_font,
            title_font_style=note_font,
        )


def _place_layer_views(
    *,
    config: AutodocConfig,
    group: AutodocGroup,
    pcbdoc: object,
    layer_views: tuple[LayerViewPlan, ...],
) -> tuple[float, tuple[LayerPlacement, ...]]:
    base_width_mm, base_height_mm = _board_size_mm(pcbdoc)
    requested_scale = group.view_scale or config.view_scale
    target_fill_ratio = group.target_fill_ratio or config.target_fill_ratio
    gap_x_mm = (
        group.tile_gap_x_mm if group.tile_gap_x_mm is not None else config.tile_gap_x_mm
    )
    gap_y_mm = (
        group.tile_gap_y_mm if group.tile_gap_y_mm is not None else config.tile_gap_y_mm
    )
    sheet = config.sheet_size.size
    header_height = _header_height_mm(group)
    available_width = sheet.width_mm - PAGE_MARGIN_MM * 2.0
    available_height = sheet.height_mm - header_height - PAGE_MARGIN_MM
    columns, rows, effective_scale = _choose_grid(
        count=len(layer_views),
        available_width=available_width,
        available_height=available_height,
        board_width_mm=base_width_mm,
        board_height_mm=base_height_mm,
        requested_scale=requested_scale,
        target_fill_ratio=target_fill_ratio,
        auto_fit=group.auto_fit_scale,
        gap_x_mm=gap_x_mm,
        gap_y_mm=gap_y_mm,
    )
    view_width = base_width_mm * effective_scale
    view_height = base_height_mm * effective_scale
    cluster_width = columns * view_width + gap_x_mm * (columns - 1)
    cluster_height = rows * view_height + gap_y_mm * (rows - 1)
    origin_left = PAGE_MARGIN_MM + max((available_width - cluster_width) / 2.0, 0.0)
    origin_bottom = PAGE_MARGIN_MM + max(
        (available_height - cluster_height) / 2.0,
        0.0,
    )
    placements: list[LayerPlacement] = []
    for index, layer_view in enumerate(layer_views):
        row = index // columns
        column = index % columns
        left = origin_left + column * (view_width + gap_x_mm)
        top = origin_bottom + (rows - row - 1) * (view_height + gap_y_mm)
        placements.append(
            LayerPlacement(
                plan=layer_view,
                left_mm=left,
                top_mm=top,
                scale=effective_scale,
                view_width_mm=view_width,
                view_height_mm=view_height,
            )
        )
    return effective_scale, tuple(placements)


def _choose_grid(
    *,
    count: int,
    available_width: float,
    available_height: float,
    board_width_mm: float,
    board_height_mm: float,
    requested_scale: float,
    target_fill_ratio: float,
    auto_fit: bool,
    gap_x_mm: float,
    gap_y_mm: float,
) -> tuple[int, int, float]:
    best: tuple[float, int, int] | None = None
    for columns in range(1, count + 1):
        rows = math.ceil(count / columns)
        cluster_width = available_width - gap_x_mm * (columns - 1)
        cluster_height = available_height - gap_y_mm * (rows - 1)
        if cluster_width <= 0.0 or cluster_height <= 0.0:
            continue
        cell_width = cluster_width / columns
        cell_height = cluster_height / rows
        fit_scale = min(cell_width / board_width_mm, cell_height / board_height_mm)
        target_scale = fit_scale * target_fill_ratio
        scale = min(requested_scale, target_scale) if auto_fit else requested_scale
        if best is None or scale > best[0]:
            best = (scale, columns, rows)
    if best is None:
        raise ValueError("cannot place zero layer views")
    return best[1], best[2], max(best[0], 0.01)


def _header_height_mm(group: AutodocGroup) -> float:
    if not group.notes:
        return MIN_HEADER_HEIGHT_MM
    notes_height = 12.0 + len(group.notes) * NOTE_ROW_HEIGHT_MM
    return max(
        MIN_HEADER_HEIGHT_MM,
        PAGE_MARGIN_MM + TITLE_HEIGHT_MM + NOTE_TOP_GAP_MM + notes_height + VIEW_GAP_MM,
    )


def _board_size_mm(pcbdoc: object) -> tuple[float, float]:
    board = getattr(pcbdoc, "board", None)
    outline = getattr(board, "outline", None)
    if outline is None:
        raise ValueError("PcbDoc does not contain a board outline")
    min_x, min_y, max_x, max_y = outline.bounding_box
    return (max_x - min_x) * 0.0254, (max_y - min_y) * 0.0254


def _rect_from_top_left(
    page: object,
    *,
    left_mm: float,
    top_mm: float,
    width_mm: float,
    height_mm: float,
) -> DraftsmanRect:
    size = page.size
    if size is None:
        raise ValueError("Draftsman page size is not available")
    return DraftsmanRect(
        x_mm=left_mm,
        y_mm=size.height_mm - top_mm - height_mm,
        width_mm=width_mm,
        height_mm=height_mm,
    )


def _primitive_matches_group(
    group: AutodocGroup, primitive: PcbDrawingPrimitive
) -> bool:
    if primitive.net_name and _casefold_member(primitive.net_name, group.nets):
        return True
    if any(_casefold_member(item, group.net_classes) for item in primitive.net_classes):
        return True
    if any(
        _casefold_member(item, group.differential_pair_classes)
        for item in primitive.differential_pair_classes
    ):
        return True
    return any(
        _casefold_member(item, group.differential_pairs)
        for item in primitive.differential_pair_names
    )


def _minimum_routing_length_mils(
    *,
    config: AutodocConfig,
    group: AutodocGroup,
) -> float:
    if group.minimum_routing_length_mils is not None:
        return group.minimum_routing_length_mils
    return config.minimum_routing_length_mils


def _connected_highlight_filter(
    *,
    config: AutodocConfig,
    group: AutodocGroup,
) -> bool:
    if group.connected_highlight_filter is not None:
        return group.connected_highlight_filter
    return config.connected_highlight_filter


def _highlighted_route_artwork(
    *,
    group: AutodocGroup,
    primitives: tuple[PcbDrawingPrimitive, ...],
    minimum_routing_length_mils: float,
    connected_highlight_filter: bool,
) -> tuple[PcbDrawingPrimitive, ...]:
    candidates = tuple(
        primitive
        for primitive in primitives
        if _is_topology_artwork_primitive(primitive)
        and _primitive_matches_group(group, primitive)
    )
    if not connected_highlight_filter:
        return tuple(
            primitive
            for primitive in candidates
            if _passes_minimum_routing_length(
                primitive,
                minimum_routing_length_mils=minimum_routing_length_mils,
            )
        )
    selected: list[PcbDrawingPrimitive] = []
    for component in _route_artwork_components(candidates):
        if _route_component_passes_threshold(
            component,
            minimum_routing_length_mils=minimum_routing_length_mils,
        ):
            selected.extend(component.primitives)
    selected_ids = {id(primitive) for primitive in selected}
    return tuple(primitive for primitive in candidates if id(primitive) in selected_ids)


def _passes_minimum_routing_length(
    primitive: PcbDrawingPrimitive,
    *,
    minimum_routing_length_mils: float,
) -> bool:
    if minimum_routing_length_mils <= 0.0:
        return True
    if primitive.primitive_kind not in {"arc", "track"}:
        return True
    return _routing_length_mils(primitive) >= minimum_routing_length_mils


def _route_component_passes_threshold(
    component: RouteArtworkComponent,
    *,
    minimum_routing_length_mils: float,
) -> bool:
    if minimum_routing_length_mils <= 0.0:
        return True
    if any(
        primitive.primitive_kind not in {"arc", "track"}
        for primitive in component.primitives
    ):
        return True
    return component.length_mils >= minimum_routing_length_mils


def _route_artwork_components(
    primitives: tuple[PcbDrawingPrimitive, ...],
) -> tuple[RouteArtworkComponent, ...]:
    components: list[RouteArtworkComponent] = []
    visited: set[int] = set()
    for start_index in range(len(primitives)):
        if start_index in visited:
            continue
        component_indices = _route_component_indices(
            primitives,
            start_index=start_index,
            visited=visited,
        )
        component_primitives = tuple(primitives[index] for index in component_indices)
        components.append(
            RouteArtworkComponent(
                primitives=component_primitives,
                length_mils=sum(
                    _routing_length_mils(item) for item in component_primitives
                ),
            )
        )
    return tuple(components)


def _route_component_indices(
    primitives: tuple[PcbDrawingPrimitive, ...],
    *,
    start_index: int,
    visited: set[int],
) -> tuple[int, ...]:
    component: list[int] = []
    pending = [start_index]
    visited.add(start_index)
    while pending:
        index = pending.pop()
        component.append(index)
        primitive = primitives[index]
        for candidate_index, candidate in enumerate(primitives):
            if candidate_index in visited:
                continue
            if _route_primitives_touch(primitive, candidate):
                visited.add(candidate_index)
                pending.append(candidate_index)
    return tuple(component)


def _route_primitives_touch(
    first: PcbDrawingPrimitive,
    second: PcbDrawingPrimitive,
) -> bool:
    if not _primitive_net_keys_intersect(first, second):
        return False
    return _primitives_touch(first, second)


def _routing_length_mils(primitive: PcbDrawingPrimitive) -> float:
    if primitive.primitive_kind == "track":
        return sum(
            max(uni.size.width_mils - uni.size.height_mils, 0.0)
            for uni in primitive.geometry.unis
        )
    if primitive.primitive_kind == "arc":
        return sum(_arc_length_mils(arc) for arc in primitive.geometry.arcs)
    return 0.0


def _arc_length_mils(arc: PcbDrawingArc) -> float:
    radius_mils = arc.radius_mils
    if radius_mils <= 0.0:
        return 0.0
    delta_degrees = (arc.end_angle_degrees - arc.start_angle_degrees) % 360.0
    if math.isclose(delta_degrees, 0.0, abs_tol=1e-9):
        delta_degrees = 360.0
    return abs(radius_mils * math.radians(delta_degrees))


def _primitive_touches_selected_artwork(
    primitive: PcbDrawingPrimitive,
    *,
    selected_artwork: tuple[PcbDrawingPrimitive, ...],
) -> bool:
    return any(
        _primitive_net_keys_intersect(primitive, selected)
        and _primitives_touch(primitive, selected)
        for selected in selected_artwork
    )


def _selected_pad_vias(
    *,
    group: AutodocGroup,
    primitives: tuple[PcbDrawingPrimitive, ...],
    selected_artwork: tuple[PcbDrawingPrimitive, ...],
    connected_highlight_filter: bool,
) -> tuple[PcbDrawingPrimitive, ...]:
    if not group.buckets.highlighted_pads_and_vias:
        return ()
    return tuple(
        primitive
        for primitive in primitives
        if primitive.role == "copper"
        and primitive.primitive_kind in {"pad", "via"}
        and _primitive_matches_group(group, primitive)
        and _highlight_pad_via_matches_selected_artwork(
            primitive,
            selected_artwork=selected_artwork,
            connected_highlight_filter=connected_highlight_filter,
        )
    )


def _highlight_pad_via_matches_selected_artwork(
    primitive: PcbDrawingPrimitive,
    *,
    selected_artwork: tuple[PcbDrawingPrimitive, ...],
    connected_highlight_filter: bool,
) -> bool:
    if connected_highlight_filter:
        return _primitive_touches_selected_artwork(
            primitive,
            selected_artwork=selected_artwork,
        )
    return _primitive_net_is_connected_to_selected_artwork(
        primitive,
        selected_artwork=selected_artwork,
    )


def _primitive_net_is_connected_to_selected_artwork(
    primitive: PcbDrawingPrimitive,
    *,
    selected_artwork: tuple[PcbDrawingPrimitive, ...],
) -> bool:
    return any(
        _primitive_net_keys_intersect(primitive, selected)
        for selected in selected_artwork
    )


def _primitive_net_keys_intersect(
    first: PcbDrawingPrimitive,
    second: PcbDrawingPrimitive,
) -> bool:
    first_keys = set(_primitive_net_keys(first))
    if not first_keys:
        return False
    return not first_keys.isdisjoint(_primitive_net_keys(second))


def _primitive_net_keys(
    primitive: PcbDrawingPrimitive,
) -> tuple[tuple[str, int | str], ...]:
    keys: list[tuple[str, int | str]] = []
    if primitive.net_index is not None:
        keys.append(("index", primitive.net_index))
    if primitive.net_name:
        keys.append(("name", primitive.net_name.casefold()))
    return tuple(keys)


def _primitives_touch(
    first: PcbDrawingPrimitive,
    second: PcbDrawingPrimitive,
) -> bool:
    for first_uni in first.geometry.unis:
        for second_uni in second.geometry.unis:
            if _unis_touch(first_uni, second_uni):
                return True
        for second_arc in second.geometry.arcs:
            if _uni_touches_arc(first_uni, second_arc):
                return True
    for first_arc in first.geometry.arcs:
        for second_uni in second.geometry.unis:
            if _uni_touches_arc(second_uni, first_arc):
                return True
        for second_arc in second.geometry.arcs:
            if _arcs_touch(first_arc, second_arc):
                return True
    if first.geometry.polygons or second.geometry.polygons:
        return _bounding_boxes_touch(first, second)
    return False


def _unis_touch(
    first: PcbDrawingUni,
    second: PcbDrawingUni,
) -> bool:
    first_start, first_end, first_radius = _uni_collision_segment(first)
    second_start, second_end, second_radius = _uni_collision_segment(second)
    distance = _segment_to_segment_distance(
        first_start, first_end, second_start, second_end
    )
    return distance <= first_radius + second_radius + GEOMETRY_TOUCH_TOLERANCE_MILS


def _uni_touches_arc(uni: PcbDrawingUni, arc: PcbDrawingArc) -> bool:
    start, end, uni_radius = _uni_collision_segment(uni)
    arc_radius = arc.thickness_mils * 0.5
    for point in (start, end):
        if (
            _point_to_arc_centerline_distance(point, arc)
            <= uni_radius + arc_radius + GEOMETRY_TOUCH_TOLERANCE_MILS
        ):
            return True
    for point in _arc_endpoints(arc):
        if (
            _point_to_segment_distance(point, start, end)
            <= uni_radius + arc_radius + GEOMETRY_TOUCH_TOLERANCE_MILS
        ):
            return True
    return False


def _arcs_touch(first: PcbDrawingArc, second: PcbDrawingArc) -> bool:
    first_radius = first.thickness_mils * 0.5
    second_radius = second.thickness_mils * 0.5
    for point in _arc_endpoints(first):
        if (
            _point_to_arc_centerline_distance(point, second)
            <= first_radius + second_radius + GEOMETRY_TOUCH_TOLERANCE_MILS
        ):
            return True
    for point in _arc_endpoints(second):
        if (
            _point_to_arc_centerline_distance(point, first)
            <= first_radius + second_radius + GEOMETRY_TOUCH_TOLERANCE_MILS
        ):
            return True
    return False


def _uni_collision_segment(
    uni: PcbDrawingUni,
) -> tuple[PcbDrawingPoint, PcbDrawingPoint, float]:
    direction_length = math.hypot(uni.direction.x, uni.direction.y)
    if direction_length <= 1e-12:
        direction_x = 1.0
        direction_y = 0.0
    else:
        direction_x = uni.direction.x / direction_length
        direction_y = uni.direction.y / direction_length
    radius = max(min(uni.size.width_mils, uni.size.height_mils) * 0.5, uni.radius_mils)
    centerline_length = max(uni.size.width_mils - radius * 2.0, 0.0)
    half_length = centerline_length * 0.5
    center = uni.location
    return (
        PcbDrawingPoint(
            center.x_mils - direction_x * half_length,
            center.y_mils - direction_y * half_length,
        ),
        PcbDrawingPoint(
            center.x_mils + direction_x * half_length,
            center.y_mils + direction_y * half_length,
        ),
        radius,
    )


def _segment_to_segment_distance(
    first_start: PcbDrawingPoint,
    first_end: PcbDrawingPoint,
    second_start: PcbDrawingPoint,
    second_end: PcbDrawingPoint,
) -> float:
    if _segments_intersect(first_start, first_end, second_start, second_end):
        return 0.0
    return min(
        _point_to_segment_distance(first_start, second_start, second_end),
        _point_to_segment_distance(first_end, second_start, second_end),
        _point_to_segment_distance(second_start, first_start, first_end),
        _point_to_segment_distance(second_end, first_start, first_end),
    )


def _point_to_segment_distance(
    point: PcbDrawingPoint,
    start: PcbDrawingPoint,
    end: PcbDrawingPoint,
) -> float:
    dx = end.x_mils - start.x_mils
    dy = end.y_mils - start.y_mils
    if math.isclose(dx, 0.0, abs_tol=1e-12) and math.isclose(dy, 0.0, abs_tol=1e-12):
        return math.hypot(point.x_mils - start.x_mils, point.y_mils - start.y_mils)
    t = ((point.x_mils - start.x_mils) * dx + (point.y_mils - start.y_mils) * dy) / (
        dx * dx + dy * dy
    )
    t = max(0.0, min(1.0, t))
    projected_x = start.x_mils + t * dx
    projected_y = start.y_mils + t * dy
    return math.hypot(point.x_mils - projected_x, point.y_mils - projected_y)


def _segments_intersect(
    first_start: PcbDrawingPoint,
    first_end: PcbDrawingPoint,
    second_start: PcbDrawingPoint,
    second_end: PcbDrawingPoint,
) -> bool:
    first_dx = first_end.x_mils - first_start.x_mils
    first_dy = first_end.y_mils - first_start.y_mils
    second_dx = second_end.x_mils - second_start.x_mils
    second_dy = second_end.y_mils - second_start.y_mils
    denominator = first_dx * second_dy - first_dy * second_dx
    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        return False
    dx = second_start.x_mils - first_start.x_mils
    dy = second_start.y_mils - first_start.y_mils
    first_t = (dx * second_dy - dy * second_dx) / denominator
    second_t = (dx * first_dy - dy * first_dx) / denominator
    return 0.0 <= first_t <= 1.0 and 0.0 <= second_t <= 1.0


def _arc_endpoints(arc: PcbDrawingArc) -> tuple[PcbDrawingPoint, PcbDrawingPoint]:
    return (
        _arc_point_at_angle(arc, arc.start_angle_degrees),
        _arc_point_at_angle(arc, arc.end_angle_degrees),
    )


def _arc_point_at_angle(arc: PcbDrawingArc, angle_degrees: float) -> PcbDrawingPoint:
    angle = math.radians(angle_degrees)
    return PcbDrawingPoint(
        arc.center.x_mils + math.cos(angle) * arc.radius_mils,
        arc.center.y_mils + math.sin(angle) * arc.radius_mils,
    )


def _point_to_arc_centerline_distance(
    point: PcbDrawingPoint,
    arc: PcbDrawingArc,
) -> float:
    dx = point.x_mils - arc.center.x_mils
    dy = point.y_mils - arc.center.y_mils
    point_radius = math.hypot(dx, dy)
    if _angle_on_arc(math.degrees(math.atan2(dy, dx)), arc):
        return abs(point_radius - arc.radius_mils)
    return min(
        math.hypot(point.x_mils - endpoint.x_mils, point.y_mils - endpoint.y_mils)
        for endpoint in _arc_endpoints(arc)
    )


def _angle_on_arc(angle_degrees: float, arc: PcbDrawingArc) -> bool:
    start = arc.start_angle_degrees % 360.0
    angle = angle_degrees % 360.0
    delta = (arc.end_angle_degrees - arc.start_angle_degrees) % 360.0
    if math.isclose(delta, 0.0, abs_tol=1e-9):
        delta = 360.0
    relative = (angle - start) % 360.0
    return relative <= delta + 1e-6


def _bounding_boxes_touch(
    first: PcbDrawingPrimitive,
    second: PcbDrawingPrimitive,
) -> bool:
    first_box = _primitive_bounding_box(first)
    second_box = _primitive_bounding_box(second)
    if first_box is None or second_box is None:
        return False
    return not (
        first_box[2] + GEOMETRY_TOUCH_TOLERANCE_MILS < second_box[0]
        or second_box[2] + GEOMETRY_TOUCH_TOLERANCE_MILS < first_box[0]
        or first_box[3] + GEOMETRY_TOUCH_TOLERANCE_MILS < second_box[1]
        or second_box[3] + GEOMETRY_TOUCH_TOLERANCE_MILS < first_box[1]
    )


def _primitive_bounding_box(
    primitive: PcbDrawingPrimitive,
) -> tuple[float, float, float, float] | None:
    boxes: list[tuple[float, float, float, float]] = []
    for uni in primitive.geometry.unis:
        start, end, radius = _uni_collision_segment(uni)
        boxes.append(
            (
                min(start.x_mils, end.x_mils) - radius,
                min(start.y_mils, end.y_mils) - radius,
                max(start.x_mils, end.x_mils) + radius,
                max(start.y_mils, end.y_mils) + radius,
            )
        )
    for arc in primitive.geometry.arcs:
        radius = arc.radius_mils + arc.thickness_mils * 0.5
        boxes.append(
            (
                arc.center.x_mils - radius,
                arc.center.y_mils - radius,
                arc.center.x_mils + radius,
                arc.center.y_mils + radius,
            )
        )
    for polygon in primitive.geometry.polygons:
        for contour in polygon.contours:
            if not contour:
                continue
            boxes.append(
                (
                    min(point.x_mils for point in contour),
                    min(point.y_mils for point in contour),
                    max(point.x_mils for point in contour),
                    max(point.y_mils for point in contour),
                )
            )
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _casefold_member(value: str, candidates: tuple[str, ...]) -> bool:
    normalized = value.casefold()
    return any(candidate.casefold() == normalized for candidate in candidates)


def _draftsman_bucket_primitives(
    primitives: tuple[PcbDrawingPrimitive, ...],
) -> tuple[DraftsmanPcbCachePrimitive, ...]:
    return tuple(
        DraftsmanPcbCachePrimitive(primitive)
        for primitive in _ordered_primitives_for_rendering(primitives)
    )


def _ordered_primitives_for_rendering(
    primitives: tuple[PcbDrawingPrimitive, ...],
) -> tuple[PcbDrawingPrimitive, ...]:
    return tuple(
        primitive
        for _, primitive in sorted(
            enumerate(primitives),
            key=lambda item: (_primitive_render_rank(item[1]), item[0]),
        )
    )


def _primitive_render_rank(primitive: PcbDrawingPrimitive) -> int:
    if primitive.role == "boardhole":
        return 4
    if primitive.primitive_kind in {"track", "arc"}:
        return 0
    if primitive.primitive_kind in {"fill", "region"}:
        return 1
    if primitive.primitive_kind in {"pad", "via"}:
        return 2
    return 3


def _as_copper_primitive(
    primitive: PcbDrawingPrimitive,
    *,
    layer: PcbLayer,
) -> PcbDrawingPrimitive:
    return replace(primitive, layer=layer, role="copper")


def _primitive_center_key(primitive: PcbDrawingPrimitive) -> tuple[object, ...] | None:
    if primitive.source_identity is not None:
        return (primitive.primitive_kind, primitive.source_identity)
    if not primitive.geometry.unis:
        return None
    location = primitive.geometry.unis[0].location
    return (
        primitive.primitive_kind,
        primitive.net_index,
        primitive.net_name,
        primitive.component_designator,
        primitive.pad_designator,
        round(location.x_mils, 6),
        round(location.y_mils, 6),
    )


def _through_hole_pad_keys(
    primitives: tuple[PcbDrawingPrimitive, ...],
) -> set[tuple[object, ...]]:
    return {
        key
        for primitive in primitives
        if primitive.role == "boardhole" and primitive.primitive_kind == "pad"
        if (key := _primitive_center_key(primitive)) is not None
    }


def _is_external_signal_layer(layer: PcbLayer) -> bool:
    return layer in {PcbLayer.TOP, PcbLayer.BOTTOM}


def _is_topology_artwork_primitive(primitive: PcbDrawingPrimitive) -> bool:
    return primitive.role == "copper" and primitive.primitive_kind in {
        "arc",
        "fill",
        "region",
        "track",
    }


def _is_smd_component_pad(
    primitive: PcbDrawingPrimitive,
    through_hole_keys: set[tuple[object, ...]],
) -> bool:
    key = _primitive_center_key(primitive)
    return (
        primitive.role == "copper"
        and primitive.primitive_kind == "pad"
        and key is not None
        and key not in through_hole_keys
    )


def _is_through_hole_component_pad(
    primitive: PcbDrawingPrimitive,
    through_hole_keys: set[tuple[object, ...]],
) -> bool:
    key = _primitive_center_key(primitive)
    return (
        primitive.role == "copper"
        and primitive.primitive_kind == "pad"
        and key is not None
        and key in through_hole_keys
    )


def _is_drill_hole_primitive(primitive: PcbDrawingPrimitive) -> bool:
    return primitive.role == "boardhole" and primitive.primitive_kind in {"pad", "via"}


def _highlight_layer_for_view(
    layer: PcbLayer,
    allocator: MechanicalBucketAllocator,
) -> PcbLayer:
    if layer == PcbLayer.BOTTOM:
        return PcbLayer.BOTTOM_SOLDER
    if layer == PcbLayer.TOP:
        return PcbLayer.TOP_SOLDER
    return allocator.allocate()


def _paste_layer_for_view(layer: PcbLayer) -> PcbLayer:
    if layer == PcbLayer.BOTTOM:
        return PcbLayer.BOTTOM_PASTE
    return PcbLayer.TOP_PASTE


def _style_colors(group: AutodocGroup) -> dict[str, DraftsmanColor]:
    return {
        "highlight": draftsman_color_from_hex_rgb(group.style.highlight_copper),
        "context": draftsman_color_from_hex_rgb(group.style.context_copper),
        "smd_pad": draftsman_color_from_hex_rgb(group.style.smd_pad_copper),
        "through_hole_pad": draftsman_color_from_hex_rgb(
            group.style.through_hole_pad_copper
        ),
        "via_pad": draftsman_color_from_hex_rgb(group.style.via_pad_copper),
        "drill_hole": draftsman_color_from_hex_rgb(group.style.drill_hole),
        "non_plated_hole": draftsman_color_from_hex_rgb(group.style.non_plated_hole),
    }


def _merge_cache_layers(
    cache_layers: Iterable[DraftsmanPcbCacheLayer],
) -> tuple[DraftsmanPcbCacheLayer, ...]:
    by_layer: dict[PcbLayer, DraftsmanPcbCacheLayer] = {}
    for cache_layer in cache_layers:
        existing = by_layer.get(cache_layer.layer)
        if existing is None:
            by_layer[cache_layer.layer] = cache_layer
            continue
        by_layer[cache_layer.layer] = replace(
            existing,
            primitives=existing.primitives + cache_layer.primitives,
        )
    return tuple(by_layer.values())


def _write_cache_fragment(
    *,
    output_dir: Path,
    output_stem: str,
    cache_layers: tuple[DraftsmanPcbCacheLayer, ...],
) -> Path:
    xml = board_layers_geometry_information_xml(cache_layers)
    output_path = output_dir / f"{output_stem}.draftsman_cache.xml"
    output_path.write_bytes(
        etree.tostring(
            xml,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )
    )
    return output_path


def _replace_document_child(
    document: AltiumDraftsmanDocument,
    new_child: etree._Element,
) -> None:
    child_name = element_local_name(new_child)
    existing = first_child_by_local_name(document.root, child_name)
    if existing is None:
        document.root.append(new_child)
        return
    parent = existing.getparent()
    if parent is None:
        document.root.append(new_child)
        return
    parent[parent.index(existing)] = new_child


def _append_page_item(page: object, item: etree._Element) -> None:
    page_element = page.element
    items = first_child_by_local_name(page_element, "Items")
    if items is None:
        items = etree.SubElement(page_element, qualified_name("Items"))
    items.append(item)


def _layer_view_summary(
    *,
    plan: LayerViewPlan,
    placement: LayerPlacement,
    stack: ResolvedLayerStack,
) -> dict[str, object]:
    return {
        **_layer_entry(plan.layer, stack),
        "view_scale": placement.scale,
        "placement_mm": {
            "left": placement.left_mm,
            "top": placement.top_mm,
            "width": placement.view_width_mm,
            "height": placement.view_height_mm,
        },
        "primitive_counts": {
            "selected_copper": _primitive_counts(plan.selected_copper),
            "context_topology": _primitive_counts(plan.context_topology),
            "context_smd_pads": _primitive_counts(plan.context_smd_pads),
            "context_through_hole_pads": _primitive_counts(
                plan.context_through_hole_pads
            ),
            "context_via_pads": _primitive_counts(plan.context_via_pads),
            "drill_holes": _primitive_counts(plan.drill_holes),
            "plated_drill_holes": _primitive_counts(plan.plated_drill_holes),
            "non_plated_drill_holes": _primitive_counts(plan.non_plated_drill_holes),
        },
        "cache_layer_count": len(plan.cache_layers),
        "display_helper_layer_count": len(plan.display_layers),
    }


def _primitive_counts(
    primitives: tuple[PcbDrawingPrimitive, ...],
) -> dict[str, int]:
    counts = Counter(primitive.primitive_kind for primitive in primitives)
    return dict(sorted(counts.items()))


def _layer_entry(layer: PcbLayer, stack: ResolvedLayerStack) -> dict[str, object]:
    return {
        "legacy_id": layer.value,
        "key": layer.to_json_name(),
        "display_name": _layer_display_name(layer, stack),
    }


def _layer_display_name(layer: PcbLayer, stack: ResolvedLayerStack) -> str:
    resolved = stack.layer_by_legacy_id(layer.value)
    return resolved.display_name if resolved is not None else layer.to_display_name()


def _layer_thickness_mils(layer: PcbLayer, stack: ResolvedLayerStack) -> float:
    resolved = stack.layer_by_legacy_id(layer.value)
    if resolved is None:
        return 0.0
    return float(resolved.thickness_mils or 0.0)


def _board_thickness_mils(stack: ResolvedLayerStack) -> float:
    return sum(float(layer.thickness_mils or 0.0) for layer in stack.layers)


def _safe_filename(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return token.strip("_").lower() or "item"


def sample_relative(path: Path, *, sample_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(sample_dir.resolve())).replace("\\", "/")
    except ValueError:
        return str(resolved).replace("\\", "/")
