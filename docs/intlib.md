# IntLib

`AltiumIntLib` is the public read-only surface for Altium integrated libraries.
Use it when you need to inspect an existing `.IntLib` package and recover the
embedded source libraries that were compiled into it.

Use it when you need to:

1. list component and model metadata from `LibCrossRef.Txt`
2. find embedded `.SchLib`, `.PcbLib`, and `.PCB3DLib` source streams
3. extract source streams to normal files
4. write a simple `.LibPkg` referencing the extracted sources
5. split extracted SchLib/PcbLib files with the normal library APIs

## Metadata Fallback

Some vendor-generated integrated libraries contain extractable source streams
but malformed cross-reference metadata. In that case `AltiumIntLib` still opens
the file and source extraction can proceed.

Check `component_parse_error` when you need to know whether component metadata
was parsed:

```python
from altium_monkey import AltiumIntLib

with AltiumIntLib("vendor.IntLib") as intlib:
    if intlib.component_parse_error:
        print(f"Component metadata unavailable: {intlib.component_parse_error}")

    result = intlib.extract_sources("extracted_sources")
```

When `component_parse_error` is set, `components` is empty because semantic
component/model cross-reference rows were not recovered. `get_source_entries()`
and `extract_sources(...)` still scan the OLE stream tree for source libraries.

## Extract-Only Boundary

This release does not compile new integrated libraries or repackage modified
sources back into an `.IntLib`. Treat IntLib support as a recovery and migration
tool: extract sources, then work with the recovered `.SchLib` and `.PcbLib`
files directly.

## Examples

Start with:

1. [`intlib_extract_sources`](../examples/intlib_extract_sources/README.md)

See [SchLib](schlib.md) and [PcbLib](pcblib.md) for working with extracted
source libraries.
