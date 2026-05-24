# PrjPcb Contract

`AltiumPrjPcb` is the public model for Altium PCB project files.

## Stable Surface

- Parse existing `.PrjPcb` project files.
- Preserve raw project configuration when a setting does not yet have a typed
  property.
- Read and write project documents, variants, parameters, output-job links, and
  class-generation settings exposed by the public API.
- Create simple project containers programmatically.

## Configuration Model

Project files are INI-like configuration documents. Typed properties are public
convenience accessors over the preserved raw configuration. Unknown keys should
survive normal read/write flows.

## Design Integration

`AltiumDesign` uses `AltiumPrjPcb` as the project-level entry point for loading
schematic sheets, PCB documents, variants, compiled netlists, and project
metadata.

## Test Gates

The PrjPcb contract is covered by project parsing, project authoring, design
loading, public examples, and release signoff.

