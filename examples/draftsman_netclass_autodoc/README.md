# Draftsman Netclass Autodoc

Experimental JSON-driven sample for generated Draftsman controlled-impedance
artwork pages.

The sample reads one or more config files, selects PCB geometry by net class,
differential-pair class, differential-pair name, or scalar net name, and emits
one Draftsman document per configured group. Each group page tiles all selected
routed-layer views onto one ANSI B sheet by default and can carry group-specific
notes and colors.

## Run

```powershell
uv run python examples\draftsman_netclass_autodoc\draftsman_netclass_autodoc.py
```

The default run processes:

- `configs/bunny_brain.json`
- `configs/rt_super_c1.json`
- `configs/loz_old_man.json`

Outputs are written under:

```text
examples/draftsman_netclass_autodoc/output
```

Each config gets its own output folder, for example:

```text
output/bunny_brain
output/rt_super_c1
output/loz_old_man
```

An explicit config can be supplied with:

```powershell
uv run python examples\draftsman_netclass_autodoc\draftsman_netclass_autodoc.py --config path\to\config.json
```

`--config` can be passed more than once.

## Config Shape

Each config has a project, default sheet/scale settings, global colors, and a
`groups` array. A group supports these selectors:

- `net_classes`
- `differential_pair_classes`
- `differential_pairs`
- `nets`

Groups can override `highlight_color`, `view_scale`, `target_fill_ratio`,
`tile_gap_x_mm`, `tile_gap_y_mm`, `auto_fit_scale`,
`minimum_routing_length_mils`, `connected_highlight_filter`, and bucket colors
through `style`. `notes` are rendered below the upper-left page title and are
excluded from the fitted tile area.

## Rendering Notes

- Highlighted copper uses the mask bucket when the source layer is top or
  bottom. The configured `minimum_routing_length_mils` threshold is applied to
  each connected routed-artwork component, so short segments remain highlighted
  when they are part of a longer connected route. Set
  `connected_highlight_filter` to `false` to revert to per-primitive threshold
  checks and same-net pad/via selection without the physical-touch filter.
- Selected pads and vias are highlighted only when the same net has highlighted
  routed artwork that physically touches them on that layer. This keeps
  via-only inner-layer pads from appearing as highlighted when no selected
  routing connects on that layer.
- Non-selected tracks, arcs, fills, and regions use topology/context coloring.
- Non-selected component pads are split into generated SMD and through-hole
  helper buckets, with colors mirrored into the native SMD/through-hole view
  settings. Free pads without component ownership are included in the same pad
  buckets.
- Non-selected via pads are cloned into a visible helper bucket.
- Through-hole pad and via drills are cloned into paste-colored geometry and a
  per-view overlay so drill openings stay visible above pad helper geometry.
  Non-plated pad holes use the JSON-configured `non_plated_hole` color.
- Draftsman renders visible `ShowedLayers` in reverse XML order. Generated
  views list drill overlays first, then pad/via helpers, then highlighted
  routes, with the visible source/context layer last so it renders underneath
  the helpers on internal-layer views.
- IPC-4761 filled/capped vias render as copper without an open drill-hole
  overlay.
- Layer tiles are clustered in the remaining page area below the title/notes.
  Tile order starts with the top layer at the top of the cluster.
- Internal signal layers use visible helper/display layers where native
  top/bottom assembly-view buckets do not map cleanly.

This remains an experimental board-assembly-view hijack. The reusable logic in
`assembly_highlight.py` is structured so future samples can swap in different
geometry selection heuristics without rewriting the Draftsman page synthesis.
