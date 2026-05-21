# pcbdoc_add_via_ipc4761_matrix

Create a PcbDoc with a matrix of vias for manual review in Altium Designer.

## What It Shows

1. `AltiumPcbDoc.add_via(...)`
2. `PcbIpc4761ViaType`
3. Ordinary top and bottom tenting flags
4. Manual solder-mask expansion fields on via records
5. Updating IPC-4761 feature rows and materials for a Type7 filling/capping via
6. Adding top-overlay labels next to authored vias for visual inspection

## Run

From the repository root:

```powershell
uv run python examples\pcbdoc_add_via_ipc4761_matrix\pcbdoc_add_via_ipc4761_matrix.py
```

## Output

```text
examples/pcbdoc_add_via_ipc4761_matrix/output/pcbdoc_add_via_ipc4761_matrix.PcbDoc
examples/pcbdoc_add_via_ipc4761_matrix/output/pcbdoc_add_via_ipc4761_matrix.json
```

Open the generated PcbDoc in Altium Designer and inspect the labeled vias. The
JSON file records the intended settings for each via in the matrix.
