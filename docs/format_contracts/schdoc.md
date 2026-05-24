# SchDoc Contract

`AltiumSchDoc` is the public document model for schematic sheets.

## Stable Surface

- Parse existing `.SchDoc` files.
- Preserve unknown or unsupported data during normal read/write flows.
- Create blank schematic documents.
- Add, insert, remove, and mutate schematic objects through document-owned
  structural APIs.
- Render schematic SVG.
- Extract and apply schematic templates.
- Preserve and extract embedded images.

## Object Ownership

SchDoc uses the `ObjectCollection` model. Typed views such as `components`,
`wires`, and `notes` are live filtered views over the owned object collection.
Use `add_object(...)`, `insert_object(...)`, `remove_object(...)`, or typed
high-level helpers for structural mutation.

Owned child records must be added through their owner:

- component pins, designators, parameters, graphics, and implementation records
  belong to components
- sheet entries, sheet-name labels, and file-name labels belong to sheet
  symbols
- harness entries and harness type labels belong to harness connectors

## Units

High-level public schematic authoring APIs use mils and expose helpers such as
`SchPointMils`, `SchRectMils`, `SchFontSpec`, and public enums.

Low-level record fields may expose source storage units when direct record
access is required.

## SVG

`AltiumSchDoc.to_svg(...)` accepts `SchSvgRenderOptions`. Normal review output
includes a root `viewBox`; strict native/oracle output may omit it by default.

See [SVG](svg.md) for the shared rendering contract.

## Test Gates

The SchDoc contract is covered by schematic authoring tests, round-trip tests,
SVG lanes, public examples, and release signoff.

