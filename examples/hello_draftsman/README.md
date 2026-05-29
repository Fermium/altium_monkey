# hello_draftsman

Create a small Altium project from scratch with one schematic, one PCB, and one
linked Draftsman `.PCBDwf` drawing.

The generated Draftsman page is A3. Its note is placed near the visual
upper-left corner by converting a top-edge offset through
`page.point_from_top_left(...)`. The Draftsman page also embeds the monkey image
and uses larger Comic Sans text for the note.

## What It Shows

1. Creating a SchDoc with text and an embedded image
2. Creating a PcbDoc with a rectangular board outline and silkscreen text
3. Creating a linked Draftsman document from the AD25 blank profile
4. Applying an A3 sheet size
5. Placing a Draftsman note by visual upper-left offset
6. Embedding an image in the Draftsman page
7. Creating a `.PrjPcb` that references the generated SchDoc, PcbDoc, and PCBDwf

## Run

From the repository root:

```powershell
uv run python examples\hello_draftsman\hello_draftsman.py
```

## Output

```text
examples/hello_draftsman/output/HELLO-DRAFTSMAN.PrjPcb
examples/hello_draftsman/output/HELLO-DRAFTSMAN.SchDoc
examples/hello_draftsman/output/HELLO-DRAFTSMAN.PcbDoc
examples/hello_draftsman/output/HELLO-DRAFTSMAN.PCBDwf
examples/hello_draftsman/output/project_manifest.json
```

Open the generated `.PrjPcb` in Altium Designer to inspect the project tree and
the linked Draftsman document.
