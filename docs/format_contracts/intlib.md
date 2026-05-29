# IntLib Contract

`AltiumIntLib` is the public reader for Altium integrated libraries.

## Stable Surface

- Open `.IntLib` files as compound library containers.
- List embedded source entries.
- Extract schematic libraries, PCB libraries, model files, and component
  metadata where available.
- Parse extracted SchLib and PcbLib payloads through the normal public models.

## Preservation Boundary

IntLib support is extraction-oriented. It is intended for source recovery and
inspection workflows. Repacking a fully equivalent integrated library is outside
the current public contract.

## Test Gates

The IntLib contract is covered by extraction tests, public examples, and release
signoff.

