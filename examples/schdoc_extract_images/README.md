# Extract SchDoc Images

Open a schematic, find embedded IMAGE records, and write each embedded image
payload to disk.

This example uses Hydroscope's top-level schematic because it contains several
placed images. The extraction API detects Altium embedded-image wrappers and
prefers the native payload when one is present. For example, a BMP preview plus
`TdxPNGImage` extracts as the native PNG bytes, preserving alpha.

Run from the package root:

```powershell
uv run python examples\schdoc_extract_images\schdoc_extract_images.py
```

The example uses:

```text
examples/assets/projects/hydroscope/TOP_LEVEL.SchDoc
```

It writes:

```text
examples/schdoc_extract_images/output/extracted_images/
examples/schdoc_extract_images/output/image_manifest.json
```

The important pattern is:

```python
schdoc = AltiumSchDoc(INPUT_SCHDOC)
written_paths = schdoc.extract_embedded_images(OUTPUT_IMAGES_DIR)
```

`AltiumSchDoc.extract_embedded_images(...)` writes one file per placed embedded
IMAGE record as `<index>__<source stem>.<detected extension>`. Linked image
records without embedded payload bytes are skipped. Plain BMP payloads remain
BMP; wrapped PNG/JPEG/GIF/SVG/WebP payloads use the native payload extension.
Avoid writing `image.image_data` directly for normal file export because it is
the raw SchDoc Storage payload and may include Altium wrapper bytes.
