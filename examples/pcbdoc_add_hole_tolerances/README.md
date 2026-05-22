# pcbdoc_add_hole_tolerances

Create a PcbDoc with labeled pad and via drill-hole tolerance examples for
manual review in Altium Designer.

## What It Shows

1. `AltiumPcbDoc.add_pad(...)` with `hole_positive_tolerance_mils` and
   `hole_negative_tolerance_mils`
2. `AltiumPcbDoc.add_via(...)` with the same tolerance options
3. Reading the authored tolerance values back through
   `hole_positive_tolerance_mils` and `hole_negative_tolerance_mils`
4. A control pad and via where the tolerance fields are left unset

## Run

From the repository root:

```powershell
uv run python examples\pcbdoc_add_hole_tolerances\pcbdoc_add_hole_tolerances.py
```

## Output

```text
examples/pcbdoc_add_hole_tolerances/output/pcbdoc_add_hole_tolerances.PcbDoc
examples/pcbdoc_add_hole_tolerances/output/pcbdoc_add_hole_tolerances.json
```

Open the generated PcbDoc in Altium Designer and inspect the labeled pads and
vias. The JSON file records the intended tolerance settings for each primitive.
