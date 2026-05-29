# draftsman_multipage_notes

Create a minimal `.PrjPcb` with empty `.SchDoc` and `.PcbDoc` files, create a
linked two-page Draftsman `.PCBDwf`, place a note on each page, reopen the
generated file, and write a JSON summary.

## What It Shows

1. Creating a blank linked Draftsman document
2. Cloning a page's sheet setup with `document.add_page(...)`
3. Adding page-scoped notes to different pages
4. Looking up pages and notes by serialized ids
5. Looking up a note by title within one page
6. Iterating document-wide notes
7. Registering generated project documents in a `.PrjPcb`

## Run

From the repository root:

```powershell
uv run python examples\draftsman_multipage_notes\draftsman_multipage_notes.py
```

## Output

```text
examples/draftsman_multipage_notes/output/draftsman_multipage_notes.PrjPcb
examples/draftsman_multipage_notes/output/draftsman_multipage_notes.SchDoc
examples/draftsman_multipage_notes/output/draftsman_multipage_notes.PcbDoc
examples/draftsman_multipage_notes/output/draftsman_multipage_notes.PCBDwf
examples/draftsman_multipage_notes/output/draftsman_multipage_notes.json
```

Open the generated project in Altium Designer, then open the generated
`.PCBDwf` and inspect both pages.
