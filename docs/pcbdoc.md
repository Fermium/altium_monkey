# PcbDoc

`AltiumPcbDoc` is the public container for PCB documents. The current release
supports parsing, extraction, SVG rendering, statistics, high-level
helper-oriented authoring, and footprint insertion.

Use it when you need to:

1. parse `.PcbDoc` files
2. inspect board geometry, layers, drills, nets, and resolved components
3. render PCB layers to SVG
4. extract embedded fonts, 3D models, or footprints
5. add board outlines, nets, PCB primitives, routes, pads, vias, and regions
6. place footprints from `.PcbLib`
7. add component bodies and embedded 3D model payloads

## Object Model

PcbDoc does not yet use the generic `ObjectCollection` API used by SchDoc and
SchLib. SchDoc/SchLib typed views are live filtered query views with explicit
structural APIs such as `add_object(...)`, `insert_object(...)`, and
`remove_object(...)`. PcbDoc instead exposes parsed records as typed lists such
as `pcbdoc.tracks`, `pcbdoc.arcs`, `pcbdoc.pads`, `pcbdoc.vias`,
`pcbdoc.regions`, `pcbdoc.texts`, and `pcbdoc.components`.

For authoring, prefer high-level helpers:

```python
pcbdoc.add_track((1000, 1000), (2000, 1000), width_mils=8, net="GND")
pcbdoc.add_pad(
    designator="1",
    position_mils=(1500, 1500),
    width_mils=60,
    height_mils=80,
)
pcbdoc.add_via(position_mils=(1750, 1500), diameter_mils=24, hole_size_mils=12)
pcbdoc.save("updated.PcbDoc")
```

Direct edits to typed lists are advanced usage. They can be appropriate for
read-preserving mutation, but callers are responsible for keeping indexes,
ownership, stream order, and related binary state valid.

PCB components are available through `pcbdoc.components`. Each
`AltiumPcbComponent` row exposes the resolved designator, footprint, placement,
rotation, side, component kind, and parsed PcbDoc component parameters. Use this
surface when a PCB-backed BOM or placement list should reflect what is actually
placed on the board.

## Units

Public PcbDoc authoring helpers use explicit `*_mils` parameter names. PCB
workflows are often metric, so convert metric source data before calling these
methods until metric helper functions are added.

Low-level PCB record fields may expose Altium internal integer units. Prefer
public helper methods for authored geometry.

## Via Protection, Tenting, And Delay

`AltiumPcbDoc.add_via(...)` can author ordinary through vias and promoted via
metadata:

```python
from altium_monkey import (
    AltiumPcbDoc,
    PcbIpc4761ViaType,
    PcbViaStructureFeatureSide,
    PcbViaStructureFeatureType,
)

pcbdoc = AltiumPcbDoc()
via = pcbdoc.add_via(
    position_mils=(1000, 1000),
    diameter_mils=24,
    hole_size_mils=10,
    ipc4761_via_type=PcbIpc4761ViaType.TYPE_7_FILLING_AND_CAPPING,
    propagation_delay_ps=12.5,
    is_tent_top=True,
    is_tent_bottom=True,
)
via.set_ipc4761_feature_side(
    PcbViaStructureFeatureType.FILLING,
    PcbViaStructureFeatureSide.BOTH,
)
via.set_ipc4761_feature_material(PcbViaStructureFeatureType.FILLING, "EPOXY")
```

Parsed vias are available through `pcbdoc.vias`. Each `AltiumPcbVia` exposes
`ipc4761_via_type`, `via_structure`, `propagation_delay_ps`, ordinary
top/bottom tenting flags, fabrication testpoint flags, and assembly testpoint
flags. The feature-table helpers `get_ipc4761_feature(...)`,
`set_ipc4761_feature(...)`, `set_ipc4761_feature_side(...)`, and
`set_ipc4761_feature_material(...)` mirror the IPC-4761 feature rows shown by
Altium Designer.

The public propagation-delay unit is picoseconds. Altium stores this field as a
seconds value in the underlying VIA payload, but callers should use
`propagation_delay_ps`.

Solder-mask expansion fields on a via are low-level record fields in Altium
internal units. They remain available for careful mutation and round-trip
preservation; use the via examples below when authoring tenting or manual mask
expansion for Altium Designer review.

## Hole Tolerances

Pads and vias expose Altium's drill-hole tolerance fields as positive and
negative magnitudes. Use the `*_mils` helpers for normal public code:

```python
pad = pcbdoc.add_pad(
    designator="1",
    position_mils=(1000, 1000),
    width_mils=150,
    height_mils=150,
    layer=PcbLayer.MULTI_LAYER,
    hole_size_mils=50,
    hole_positive_tolerance_mils=3.0,
    hole_negative_tolerance_mils=2.0,
)

via = pcbdoc.add_via(
    position_mils=(1400, 1000),
    diameter_mils=28,
    hole_size_mils=12,
    hole_positive_tolerance_mils=1.5,
    hole_negative_tolerance_mils=0.5,
)
```

For mutation, assign `pad.hole_positive_tolerance_mils`,
`pad.hole_negative_tolerance_mils`, `via.hole_positive_tolerance_mils`, or
`via.hole_negative_tolerance_mils`. A value of `None` represents Altium's N/A
state; the raw fields remain available as internal-unit integers for advanced
round-trip work.

## Current Gaps

PcbDoc does not yet use `ObjectCollection`.

There is no public generic PcbDoc object deletion API in this release.

Mutations outside the high-level helper methods generally require direct
record-list edits and should be validated carefully.

## Examples

Start with:

1. [`hello_pcbdoc`](../examples/hello_pcbdoc/README.md)
2. [`pcbdoc_stats`](../examples/pcbdoc_stats/README.md)
3. [`pcbdoc_bom`](../examples/pcbdoc_bom/README.md)
4. [`pcbdoc_pick_n_place`](../examples/pcbdoc_pick_n_place/README.md)
5. [`pcbdoc_svg`](../examples/pcbdoc_svg/README.md)
6. [`pcbdoc_netclass_svg`](../examples/pcbdoc_netclass_svg/README.md)
7. [`pcbdoc_add_track`](../examples/pcbdoc_add_track/README.md)
8. [`pcbdoc_add_arc`](../examples/pcbdoc_add_arc/README.md)
9. [`pcbdoc_add_pad`](../examples/pcbdoc_add_pad/README.md)
10. [`pcbdoc_add_hole_tolerances`](../examples/pcbdoc_add_hole_tolerances/README.md)
11. [`pcbdoc_add_via_ipc4761_matrix`](../examples/pcbdoc_add_via_ipc4761_matrix/README.md)
12. [`pcbdoc_mutate_via_ipc4761`](../examples/pcbdoc_mutate_via_ipc4761/README.md)
13. [`pcbdoc_add_text`](../examples/pcbdoc_add_text/README.md)
14. [`pcbdoc_add_filled_region`](../examples/pcbdoc_add_filled_region/README.md)
15. [`pcbdoc_insert_nets_route`](../examples/pcbdoc_insert_nets_route/README.md)
16. [`pcbdoc_insert_footprint_from_pcblib`](../examples/pcbdoc_insert_footprint_from_pcblib/README.md)
17. [`pcbdoc_extract_pcblib`](../examples/pcbdoc_extract_pcblib/README.md)
18. [`pcbdoc_extract_embedded_3d_models`](../examples/pcbdoc_extract_embedded_3d_models/README.md)
19. [`pcbdoc_extract_embedded_fonts`](../examples/pcbdoc_extract_embedded_fonts/README.md)

See [API patterns](api_patterns/index.md) for public vs careful mutation
guidance.
