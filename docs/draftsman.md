# Draftsman

`AltiumDraftsmanDocument` provides an experimental Python-first API for PCB
Draftsman `.PCBDwf` files. This surface is intentionally narrow and can change
as more Draftsman object families are promoted into typed wrappers.

Supported operations:

1. load raw XML or legacy LZ4-compressed Draftsman containers
2. save raw XML Draftsman outputs that Altium Designer can open
3. create a blank AD25-profile document from the packaged template
4. set the linked source PcbDoc filename
5. inspect pages and page items while preserving unknown XML subtrees
6. inspect and mutate note titles, note rows, and note row membership
7. inspect and update page size, margins, sheet sizing mode, zones, document
   default font, sheet color, border color, grid visibility, and grid size
8. add/reuse document font-style records and create simple note items
9. apply Altium standard sheet sizes such as `A3`
10. create note rows with typed border styles such as circle, square, box, and
   flag
11. create and inspect text items with typed rectangles, font style ids, colors,
    and horizontal/vertical alignment
12. create and inspect picture items with embedded bitmap bytes and
    maintain-aspect-ratio settings

Draftsman support is intentionally conservative. Unsupported objects remain as
raw XML and are preserved when the document is saved. Saving currently writes
raw XML containers; LZ4 write support is reserved by the API but not implemented
yet.

## Fonts

Draftsman `.PCBDwf` files store document font styles as family name, size, and
decoration flags. They do not currently expose embedded custom font payloads in
the document font-style records. If you use a custom font family, install that
font on machines that will open or render the Draftsman document.

Font decoration flags use Altium's Draftsman values:

| Flag | Meaning |
| --- | --- |
| `1` | italic |
| `2` | bold |
| `4` | underline |
| `8` | strikeout |

## Geometry Units

Draftsman serializes page and note geometry as drawing points at 96 points per
inch. The public Python fields ending in `_mm` convert to and from millimeters.
For example, `page.add_note(x_mm=20, y_mm=30, width_mm=250)` writes the
corresponding serialized drawing-point values into the `.PCBDwf`.

Draftsman page coordinates use a lower-left origin. X increases to the right
and Y increases toward the top of the sheet. For visual placement from the
upper-left corner, use `page.point_from_top_left(left_mm=..., top_mm=...)` and
pass the returned point into `page.add_note(...)`.

Use `DraftsmanStandardSheetSize` for standard page sizes instead of writing raw
dimensions directly.

## Text And Pictures

`page.add_text(...)` creates a Draftsman `Text` item. The rectangle is a
`DraftsmanRect` in page millimeters, and alignment uses
`DraftsmanHorizontalAlignment` and `DraftsmanVerticalAlignment`. By default,
text items use `fill_style_id=0`, which leaves the fill style unresolved and
lets Altium load the text with transparent fill. Use a real document fill-style
id only when you intentionally want a visible fill behind the text.
When a text or note helper receives an explicit font style, it also clears the
matching `UseDocumentFont` flag so Altium uses the requested style.

`page.add_picture(...)` creates a Draftsman `Picture` item from embedded image
bytes. Draftsman stores PNG images in the legacy `Bitmap` payload and stores
non-PNG bitmap formats in the current `Bitmap2` payload with a small PNG
placeholder in `Bitmap`, matching observed Altium serialization behavior. Use
bitmap formats that Altium can load, such as PNG, JPEG, GIF, or BMP. SVG files
are rasterized by Altium's UI before serialization and are not rasterized by
this helper.

## Note Border Styles

`DraftsmanNoteBorderStyle` mirrors Altium's note/callout reference border enum:

| Enum | Label |
| --- | --- |
| `NONE` | None |
| `SQUARE` | Square |
| `CIRCLE` | Circle |
| `TRIANGLE` | Triangle |
| `UNDERLINE` | Underline |
| `BOX` | Box |
| `OBLONG` | Oblong |
| `CIRCLE_GOST` | Circle (GOST) |
| `TRIANGLE_GOST` | Triangle (GOST) |
| `HEXAGON` | Hexagon |
| `FLAG` | Flag |

## Example

```python
from altium_monkey import (
    AltiumDraftsmanDocument,
    DraftsmanColor,
    DraftsmanHorizontalAlignment,
    DraftsmanNoteBorderStyle,
    DraftsmanRect,
    DraftsmanStandardSheetSize,
    DraftsmanVerticalAlignment,
)

doc = AltiumDraftsmanDocument.blank(source_document_name="board.PcbDoc")
font = doc.get_or_create_font_style("Arial", 10, bold=True)

doc.document_options.set_font_style(font)
doc.document_options.sheet_color = DraftsmanColor.rgb(245, 245, 245)
doc.document_options.grid_color = DraftsmanColor.rgb(243, 243, 243)

page = doc.pages[0]
page.apply_standard_sheet_size(DraftsmanStandardSheetSize.A3)
upper_left = page.point_from_top_left(left_mm=6, top_mm=8)
note = page.add_note(
    title="GENERAL NOTES",
    x_mm=upper_left.x_mm,
    y_mm=upper_left.y_mm,
    width_mm=250,
    bullets=("Fabricate per IPC-6012.", "Inspect before shipment."),
    element_font_style=font,
)
note.add_element("Flagged follow-up item.", border_style=DraftsmanNoteBorderStyle.FLAG)

image_rect = page.rect_centered(width_mm=80, height_mm=80)
text_rect = DraftsmanRect(
    x_mm=image_rect.x_mm - 20,
    y_mm=image_rect.y_mm + image_rect.height_mm + 10,
    width_mm=image_rect.width_mm + 40,
    height_mm=12,
)
page.add_text(
    text="altium-monkey wuz here",
    rect=text_rect,
    font_style=font,
    horizontal_alignment=DraftsmanHorizontalAlignment.CENTER,
    vertical_alignment=DraftsmanVerticalAlignment.CENTER,
)
page.add_picture(source_path="monkey.png", rect=image_rect)

doc.save("drawing.PCBDwf")
```

See the
[`draftsman_create_blank_project`](../examples/draftsman_create_blank_project/README.md)
and [`hello_draftsman`](../examples/hello_draftsman/README.md) examples for
project-level flows that create linked `.PCBDwf` files and add them to
`.PrjPcb` projects. See
[`draftsman_add_image`](../examples/draftsman_add_image/README.md) for a
minimal text-plus-image synthesis flow.
