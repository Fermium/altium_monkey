# pcbdoc_add_differential_pairs

Create a PcbDoc from scratch, add differential-pair objects, add routed copper
segments and vias on the member nets, then save the generated board.

## What It Shows

1. Creating an `AltiumPcbDoc()` without an input board
2. Defining a rectangular board outline
3. Adding pair objects with `AltiumPcbDoc.add_differential_pair(...)`
4. Letting pair authoring create missing positive and negative nets
5. Routing tracks and vias on the pair member nets
6. Saving and reparsing the generated board to write a JSON summary

## Run

From the repository root:

```powershell
uv run python examples\pcbdoc_add_differential_pairs\pcbdoc_add_differential_pairs.py
```

## Output

```text
examples/pcbdoc_add_differential_pairs/output/pcbdoc_add_differential_pairs.PcbDoc
examples/pcbdoc_add_differential_pairs/output/pcbdoc_add_differential_pairs.json
```

Open the output PcbDoc in Altium Designer and inspect the PCB panel's
differential-pair entries for `USB_D`, `CAM_D0`, and `LVDS_CLK`.
