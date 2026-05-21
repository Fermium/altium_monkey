# pcbdoc_mutate_via_ipc4761

Copy the RT Super C1 project into this example's `output` folder, find all
12 mil diameter / 6 mil hole vias in the copied PcbDoc, and mark them as
IPC-4761 Type7 filling and capping.

The sample uses Type7 with an epoxy filling row and copper capping row as a
practical representation of epoxy-filled and capped/plated vias.

## What It Shows

1. Loading an existing PcbDoc with `AltiumPcbDoc.from_file(...)`
2. Finding vias by low-level diameter and hole fields
3. Setting `via.ipc4761_via_type`
4. Updating IPC-4761 feature row side and material values
5. Saving the mutated project copy without changing the source asset

## Run

From the repository root:

```powershell
uv run python examples\pcbdoc_mutate_via_ipc4761\pcbdoc_mutate_via_ipc4761.py
```

## Input Project

```text
examples/assets/projects/rt_super_c1/RT_SUPER_C1.PrjPcb
```

## Output

```text
examples/pcbdoc_mutate_via_ipc4761/output/rt_super_c1_type7_filled_vias/RT_SUPER_C1.PrjPcb
examples/pcbdoc_mutate_via_ipc4761/output/rt_super_c1_type7_filled_vias/RT_SUPER_C1.PCBdoc
examples/pcbdoc_mutate_via_ipc4761/output/mutation_summary.json
```

Open the output project in Altium Designer and inspect the 12/6 mil vias.
