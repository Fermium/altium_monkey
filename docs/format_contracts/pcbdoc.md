# PcbDoc Contract

`AltiumPcbDoc` is the public board model for PCB documents.

## Stable Surface

- Parse existing `.PcbDoc` files.
- Preserve unknown streams and unsupported fields during normal read/write
  flows.
- Create blank PCB documents.
- Add common board primitives with high-level helper methods.
- Add nets, net classes, differential pairs, components, footprints, vias,
  tracks, arcs, regions, pads, text, and component bodies.
- Embed STEP models and infer component-body projection bounds through the core
  `wn-geometer` dependency, with explicit projection overrides available for
  deterministic authored geometry.
- Read and write promoted via metadata such as IPC-4761 type, via feature
  rows, solder-mask tenting, hole tolerance, fabrication/assembly testpoint
  flags, and propagation delay.
- Render PCB SVG and PCB layer SVGs.

## Object Model

PcbDoc is helper-oriented rather than `ObjectCollection`-based. Prefer
document-owned helpers such as `add_track(...)`, `add_via(...)`,
`add_component(...)`, `add_differential_pair(...)`, and related APIs.

Direct record-list mutation remains an advanced escape hatch for narrow edits
or preservation work.

## Units

High-level PCB helper methods use explicit `*_mils` parameter names. Low-level
record fields may expose source integer storage units.

## Embedded 3D Models

STEP-derived component-body bounds use `wn-geometer`. If STEP bounds cannot be
computed on the current host, authoring helpers may use an axis-aligned
rectangle around available SMD/through-hole pads as a recovery projection. This
fallback is not a replacement for STEP-derived model geometry.

## Layer Names

Stable layer keys use token names such as `TOP`, `BOTTOM`, and `TOPOVERLAY`.
Use the resolved layer stack when board-specific user-facing names are needed.
Default display labels are fallback labels, not stable identifiers.

## SVG

`AltiumPcbDoc.to_svg(...)`, `to_layer_svgs(...)`, and
`to_board_outline_svg(...)` accept `PcbSvgRenderOptions`. Normal output
includes a root `viewBox` in millimeter coordinates.

See [SVG](svg.md) for the shared rendering and enrichment contract.

## Test Gates

The PcbDoc contract is covered by foundation parsing, authoring, round-trip,
SVG, public examples, and release signoff.

