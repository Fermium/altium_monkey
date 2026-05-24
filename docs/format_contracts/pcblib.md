# PcbLib Contract

`AltiumPcbLib` is the public model for PCB footprint libraries.

## Stable Surface

- Parse existing `.PcbLib` files.
- Preserve unknown or unsupported data during normal read/write flows.
- Create new footprint libraries.
- Add, find, split, and render footprints.
- Add pads, tracks, arcs, regions, text, vias, component bodies, and embedded
  STEP models to footprints.
- Extract embedded 3D model payloads.

## Object Model

`AltiumPcbLib` owns footprints and embedded model streams.
`AltiumPcbFootprint` owns its primitive lists and helper methods. Attach a
footprint to a library before adding primitives that need library-owned streams
or metadata.

## Units

High-level footprint helper methods use explicit mil-unit parameter names.
Low-level record fields may expose source integer storage units.

## Layer Names

PcbLib footprints do not have a board layer stack. Stable layer keys use token
names, and default display labels are used only for human-facing labels.

## SVG

`AltiumPcbFootprint.to_svg(...)` and `to_layer_svgs(...)` accept
`PcbSvgRenderOptions`. Normal output includes a root `viewBox` in millimeter
coordinates.

See [SVG](svg.md) for the shared rendering contract.

## Test Gates

The PcbLib contract is covered by footprint parsing, split/extract, authoring,
3D model, SVG, public examples, and release signoff.

