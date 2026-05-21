# altium-monkey 2026.05.20 Release Notes

Package version: `2026.5.20`

`2026.05.20` is represented in Python package metadata as the PEP 440
canonical form `2026.5.20`.

This release promotes PcbDoc via-protection metadata into the Python public API
and adds public examples for authoring and mutating IPC-4761 via settings. It
also carries forward the parser, rendering, deterministic-output, and PcbLib
metadata fixes from the previous package version.

## New PcbDoc Via APIs

### IPC-4761 Via Protection

`AltiumPcbVia` now exposes `ipc4761_via_type` for the IPC-4761 type shown in
Altium Designer's Via dialog. The public enum is `PcbIpc4761ViaType` and maps
directly to Altium's values from `NONE` through
`TYPE_7_FILLING_AND_CAPPING`.

The structured IPC-4761 feature rows are available through
`via.via_structure` and helper methods:

1. `via.get_ipc4761_feature(...)`
2. `via.set_ipc4761_feature(...)`
3. `via.set_ipc4761_feature_side(...)`
4. `via.set_ipc4761_feature_material(...)`

Feature row types and sides use `PcbViaStructureFeatureType` and
`PcbViaStructureFeatureSide`.

### Via Propagation Delay

`AltiumPcbVia.propagation_delay_ps` provides read/write access to the via
propagation-delay field in picoseconds. `AltiumPcbDoc.add_via(...)` and the
underlying PcbDoc builder accept `propagation_delay_ps=...` for new vias.

Altium stores this value as seconds in the binary VIA payload. The public API
uses picoseconds to match the Via dialog and to avoid exposing the serializer's
unit convention to normal callers.

### Tenting, Mask, And Testpoint Metadata

`AltiumPcbDoc.add_via(...)` now accepts:

1. `is_tent_top`
2. `is_tent_bottom`
3. `is_test_fab_top`
4. `is_test_fab_bottom`
5. `is_assy_testpoint_top`
6. `is_assy_testpoint_bottom`

Authored tented vias now emit the manual solder-mask state that Altium
Designer expects for ordinary via tenting to survive an open/save cycle.

## Examples

Two public examples were added:

1. `pcbdoc_add_via_ipc4761_matrix` creates a labeled PcbDoc via matrix covering
   IPC-4761 types, ordinary tenting, manual solder-mask expansion variants, and
   a Type7 epoxy-fill/copper-cap example.
2. `pcbdoc_mutate_via_ipc4761` copies the bundled RT Super C1 project, finds
   12 mil diameter / 6 mil hole vias, and marks them as IPC-4761 Type7 filling
   and capping with explicit feature-row metadata.

## Bug Fixes

### PcbDoc Via Propagation-Delay Units Are Consistent

The public `propagation_delay_ps` API consistently uses picoseconds while the
serializer reads and writes the underlying VIA payload float in seconds.

Freshly authored propagation-delay values now include the Altium-compatible VIA
tail marker/default bytes needed for values to survive an Altium Designer
open/save cycle.

### PcbDoc Ordinary Tenting Authors Altium-Compatible Mask State

`add_via(..., is_tent_top=True)` and
`add_via(..., is_tent_bottom=True)` now emit manual solder-mask expansion state
with compatible defaults. This allows ordinary tenting flags to persist through
Altium Designer rather than being canonicalized away.

### PCB SVG Skips Text Records With No Drawable Glyph Geometry

PCB text records whose resolved glyphs produce no drawable geometry now emit no
SVG path output. This prevents empty or placeholder text geometry from
appearing when a font cannot provide visible outlines for a record.

### Fixed-Width PCB UTF-16 Text Fields Decode Safely

Fixed-width UTF-16-LE PCB text fields now decode through a safer path that
handles truncated or partially populated buffers defensively.

### PcbLib Footprint Regions Handle Extended-Vertex Records

Some footprint `Data` streams store shape-based region geometry under the
standard `REGION` record discriminator while using the extended, arc-capable
vertex layout. PcbLib extraction now detects that layout and preserves the
shape-based region geometry instead of treating the payload as a simple region.

### PCB Metadata Follows Windows-1252 Text Semantics

PcbDoc and PcbLib pipe-text metadata now uses Windows-1252 encoding and
decoding to match Altium's native serializer. This fixes footprint extraction
and library authoring for real-world files that contain Windows-1252
punctuation bytes.

### Schematic And Design-Output Stability Fixes

This release carries forward the schematic rendering, symbol extraction,
deterministic design JSON/netlist/PNP output, and SchLib preview parity fixes
from the previous package version.

## Public API Compatibility

Existing documented APIs remain compatible. The release adds optional keyword
arguments to `AltiumPcbDoc.add_via(...)` and adds public enum/model surfaces
for via IPC-4761 metadata, feature rows, propagation delay, tenting, and
testpoint flags.

Exact serialized ordering for design JSON, netlist, and PNP data may change in
golden-file tests because output ordering is now more deterministic. PCB text
metadata now normalizes Windows-1252 byte streams to Unicode strings on read and
serializes those fields as Windows-1252 on write.

We strive to maintain compatibility for documented public APIs between
releases. The API surface may still change as more Altium capabilities are
modeled, especially in areas listed as known functional gaps. Compatibility
notes and migration guidance will be documented in release notes.

## Supported Python Versions

This release supports Python 3.11 and Python 3.12.

Python 3.13 is not advertised yet. The core package may work on Python 3.13, but
the CadQuery/OCCT/VTK dependency path used for STEP model bounds has not been
validated on Python 3.13.

## Functional Gaps

### PcbDoc Authoring And Object Model

The PcbDoc API includes high-level helper-oriented authoring for common board
workflows: outline/origin/layer-stack setup, nets, components, footprint
placement from PcbLib, tracks, arcs, fills, text, pads, vias, IPC-4761 via
metadata, regions, component bodies, embedded model payloads, and STEP-backed
3D body placement.

This is intentionally different from the current schematic object model.
SchDoc and SchLib use `ObjectCollection` with live filtered views and explicit
structural APIs such as `add_object(...)`, `insert_object(...)`, and
`remove_object(...)`. PcbDoc still exposes parsed board data through typed lists
plus PCB-specific high-level helpers. It does not yet use `ObjectCollection`.

Known gaps:

1. There is no generic `ObjectCollection`-style PcbDoc mutation/deletion API
   yet.
2. There is no public generic PcbDoc object deletion API yet.
3. Existing PcbDoc mutations outside the high-level helper methods generally
   require direct record-list edits. Treat those edits as advanced usage and
   validate outputs in Altium Designer.

### IntLib Support

Integrated libraries are extract-only in this release.

Supported:

1. Extract source files from an existing IntLib.
2. Split extracted SchLib/PcbLib files when they contain multiple symbols or
   footprints.
3. Continue source extraction when component cross-reference metadata is
   malformed but embedded source streams are still present.

Not supported:

1. Compile or build a new IntLib.
2. Repackage modified sources back into an IntLib.
3. Recover semantic component/model metadata when the source IntLib's
   cross-reference stream cannot be parsed.

### Hierarchical Designs And Annotation Files

Complex hierarchical sheets, multi-channel designs, and designator resolution
may have edge cases in `altium_design.py`.

Altium Designer can store board-level annotation changes in `*.Annotation`
files for cases such as device sheets and multi-channel designs. This release
does not process those annotation files. Designs that depend on annotation-file
mapping may need additional validation.

Reference:

https://www.altium.com/documentation/altium-designer/schematic/annotating-design-components#component-linking-with-unique-ids

Please file an issue with a minimal reproducible project if you find a
hierarchical design or annotation-resolution case that is not represented
correctly.

### Variant Processing

Project variant support includes `ProjectVariantN` parsing, current-variant
selection, DNP/not-fitted designator lists, raw variation rows, variant-level
parameter rows, per-designator `ParamVariation` parameter overrides, and
variant metadata in design JSON.

`AltiumDesign.to_bom(variant=...)` applies parameter overrides to component
parameter maps, display values, and descriptions while retaining DNP rows with a
`dnp` flag. `AltiumDesign.to_pnp(variant=...)` omits DNP placements for the
selected variant.

Alternate fitted component rows are preserved in raw variant metadata but are
not applied as semantic component replacements in BOM, netlist, PNP, or SVG
output yet. Variant-aware schematic SVG presentation is also outside the core
public API for this release.

### Platform Coverage

Primary release validation remains on Windows.

Basic package operation has also been checked on macOS, including baseline
functional SVG font substitution. Linux coverage remains limited, and exact SVG
font metrics may still vary by installed system fonts and local fallback
behavior.
