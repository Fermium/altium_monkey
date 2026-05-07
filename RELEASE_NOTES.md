# altium-monkey 2026.05.07 Release Notes

Package version: `2026.5.7`

`2026.05.07` is represented in Python package metadata as the PEP 440
canonical form `2026.5.7`.

## Bug Fixes

IntLib source extraction is more tolerant of vendor-generated integrated
libraries with malformed `LibCrossRef.Txt` component metadata. `AltiumIntLib`
now records the cross-reference parse failure on `component_parse_error` and
continues to discover extractable `.SchLib`, `.PcbLib`, and `.PCB3DLib` source
streams by scanning the OLE stream tree.

PCB SVG rendering now keeps unlinked copper regions in the normal copper layer
color. This improves previews for vendor custom pad shapes that arrive as
unlinked `ShapeBasedRegion` or region primitives. Linked polygon pours still use
the configured polygon overlay color.

## Documentation

The public docs now include an IntLib guide covering source extraction,
metadata fallback behavior, and the extract-only support boundary.

The release-process documentation and `.env.example` now document the Twine
environment variables used by the release wrapper.

## Public API Compatibility

The `AltiumIntLib.component_parse_error` property is additive. Existing IntLib
code that reads `components`, `get_source_entries()`, `read_stream(...)`, or
`extract_sources(...)` should continue to work.

We strive to maintain compatibility for documented public APIs between
releases. The API surface may still change as more Altium capabilities are
modeled, especially in areas listed as known functional gaps. Compatibility
notes and migration guidance will be documented in release notes.

## Supported Python Versions

This release supports Python 3.11 and Python 3.12.

Python 3.13 is not advertised yet. The core package may work on Python 3.13, but
the CadQuery/OCCT/VTK dependency path used for STEP model bounds has not been
validated through the full release pipeline on Python 3.13.

## Functional Gaps

### PcbDoc Mutation API

The PcbDoc API is currently focused on parsing, extraction, rendering, and
targeted authoring helpers.

Known gaps:

1. There is no generic `ObjectCollection`-style query API for PcbDoc yet.
2. There is no public PcbDoc object deletion API yet.
3. Existing PcbDoc mutations outside the high-level helper methods generally
   require direct record-list edits. Treat those edits as advanced usage and
   validate outputs in Altium Designer.

The intended direction for a follow-up release is to bring the PcbDoc mutation
surface closer to the SchDoc/SchLib object model.

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

Variant processing includes DNP handling and parameter overrides for this
release.

Other variant behaviors, such as alternate fitted components and variant-aware
SVG presentation, are not part of the core public API yet.

### Platform Coverage

Primary release validation has been on Windows.

Linux and macOS testing is minimal for this release. The SVG font substitution
path may need additional platform-specific validation because available system
fonts and font fallback behavior vary by machine.
