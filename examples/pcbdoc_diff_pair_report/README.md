# pcbdoc_diff_pair_report

Load the RT Super C1 project, read the PCB differential-pair objects, print a
small table, and write JSON plus text reports.

The bundled RT Super C1 asset currently contains `USB_D` with member nets
`USB_D_P` and `USB_D_N`. If the reference project is updated with more
differential pairs, the sample reports them without code changes.

## What It Shows

1. Loading a project with `AltiumDesign.from_prjpcb(...)`
2. Opening its PcbDoc with `design.load_pcbdoc()`
3. Iterating `pcbdoc.differential_pairs`
4. Reading `pcbdoc.differential_pair_classes`
5. Using `pcbdoc.differential_pairs_by_net_name`
6. Writing human-readable and machine-readable reports

## Run

From the repository root:

```powershell
uv run python examples\pcbdoc_diff_pair_report\pcbdoc_diff_pair_report.py
```

## Input Project

```text
examples/assets/projects/rt_super_c1/RT_SUPER_C1.PrjPcb
```

## Output

```text
examples/pcbdoc_diff_pair_report/output/pcbdoc_diff_pair_report.json
examples/pcbdoc_diff_pair_report/output/pcbdoc_diff_pair_report.txt
```
