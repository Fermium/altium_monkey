# AltiumDesign Contract

`AltiumDesign` is the public project-level loader and integration model.

## Stable Surface

- Load an Altium project from `.PrjPcb`.
- Discover schematic, PCB, library, harness, and output-job documents where
  supported.
- Build compiled schematic netlists.
- Emit JSON design and netlist payloads with declared schema ids.
- Render project-level schematic SVG outputs.

## Schema Contracts

JSON payloads include explicit schema ids such as `altium_monkey.design.a1` and
`altium_monkey.netlist.a0`. Breaking JSON payload changes require a new schema
id. Additive fields may appear within the current schema when existing fields
keep their meaning.

## SVG Linkage

Design JSON may carry ids that link back to schematic SVG output.
`components[].svg_id` points to the rendered component group id, and optional
`indexes.svg_to_component` maps SVG ids back to component designators.
Netlist records carry `nets[].graphical` and `nets[].endpoints` for schematic
highlighting and semantic trace workflows.

See [SVG](svg.md) for the SVG-side contract.

## Boundary

`AltiumDesign` exposes Altium-native project data. Cross-CAD normalization is a
separate consumer concern.

## Test Gates

The AltiumDesign contract is covered by design loading, netlist, JSON schema,
SVG, public examples, and release signoff.
