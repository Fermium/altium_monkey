# draftsman_create_blank_project

Create a blank Draftsman `.PCBDwf` file linked to an existing copied PcbDoc.

## What It Shows

1. Creating a Draftsman document from the packaged AD25 blank profile
2. Setting the linked source PcbDoc filename
3. Saving the generated `.PCBDwf`
4. Adding the generated `.PCBDwf` to the copied `.PrjPcb`
5. Reopening the generated file through `AltiumDraftsmanDocument`
6. Copying a project folder for manual Altium Designer review

Draftsman support is intentionally conservative. The current API can load,
save, create blank documents, inspect pages/items/notes, mutate existing note
text and note-element membership, inspect page/document style settings, and
create simple note items. It also exposes standard sheet-size and note
border-style enums for synthesis. It does not yet create new board views from
scratch.

## Run

From the repository root:

```powershell
uv run python examples\draftsman_create_blank_project\draftsman_create_blank_project.py
```

## Output

```text
examples/draftsman_create_blank_project/output/RT_SUPER_C1_BLANK_DRAFTSMAN/
examples/draftsman_create_blank_project/output/RT_SUPER_C1_BLANK_DRAFTSMAN/RT_SUPER_C1_Blank.PCBDwf
examples/draftsman_create_blank_project/output/draftsman_create_blank_project.json
```

For manual review, open the copied project under the output folder in Altium
Designer. The project should list `RT_SUPER_C1_Blank.PCBDwf`; open it from the
project tree. The Draftsman document should open as a blank drawing linked to
the copied `RT_SUPER_C1.PCBdoc`.
