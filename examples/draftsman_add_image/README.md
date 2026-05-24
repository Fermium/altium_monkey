# draftsman_add_image

Create a Draftsman `.PCBDwf` from the packaged AD25 blank profile, place a
centered embedded image, and place a text string above it. The example also
sets a smaller sheet border-zone band and a small document default font while
using a larger explicit font for the text item.

## What It Shows

1. Creating a blank Draftsman document
2. Applying an A3 sheet size
3. Adjusting the sheet margin used by Draftsman's border zones
4. Centering a Draftsman rectangle with `page.rect_centered(...)`
5. Adding a text item with alignment and font style
6. Adding an embedded picture item from local image bytes while preserving the
   source image aspect ratio
7. Saving and reopening the generated `.PCBDwf`

## Run

From the repository root:

```powershell
uv run python examples\draftsman_add_image\draftsman_add_image.py
```

## Output

```text
examples/draftsman_add_image/output/draftsman_add_image.PCBDwf
examples/draftsman_add_image/output/draftsman_add_image.json
```

Open the generated `.PCBDwf` in Altium Designer to manually inspect the centered
image and the text string above it.
