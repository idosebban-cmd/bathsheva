# Atelier manual

Printed instruction booklet for Atelier (Bathsheva London), A6, saddle-stitched, 16 pages.

## Status: Phase 2 draft built

```
python3 manual/build.py
```

rebuilds `manual/out/atelier-manual.pdf` plus one PNG preview per page and
`manual/out/tbd_report.txt` (every `TBD_FROM_ODM` value still in the PDF,
grouped by page). `manual/out/` is gitignored -- it's a build artifact,
regenerate it rather than expecting it to be checked in.

- [x] Page outline -- `outline.md` (16 pages, revised per review)
- [x] Hardware spec decisions -- `specs.yaml`
- [x] Illustrations -- `scripts/lineart.py` + `scripts/assembly.yaml`, see below
- [x] `content.md` -- the manual's copy, pulls every hardware fact from `specs.yaml`
- [x] `build.py` -- one command, HTML -> PDF + page PNGs, magenta TBD styling,
      automatic overflow detection (fails the build rather than silently
      clipping a page)
- [ ] Real CAD source for grille/bezel/knob/fin placement (see below) --
      still not found; current art is photo/mesh-fitted and provisional

## Folder layout

```
manual/
  models/         Source STLs + PRINT_NOTES.md
  reference/      Reference photo used for fitted_by_eye placement
  scripts/
    assembly.yaml       Per-part transforms, print-orientation -> real assembly
    lineart.py          Core engine: assembles parts, extracts silhouette +
                          crease edges, removes hidden lines by real ray-cast
                          occlusion, writes single-weight black-line SVGs
    refit_from_mesh.py  Finds grille/bezel/knob/fin mounting points from
                          witness marks already in body.stl (see below)
    photo_fit.py        Original photo-pixel-based fitting (mostly
                          superseded by refit_from_mesh.py; still used for
                          the fin tip / footprint radius)
    make_figures.py     Generates the actual figures used in the manual
                          into figures/final/
    annotate_knob.py    Adds the turn/press/hold schematic arrows to the
                          knob close-up
    render_pdf.js       Playwright: HTML -> PDF + per-page PNGs, checks for
                          page overflow
  figures/
    test/           Phase 1 proof-of-concept renders (kept for reference)
    final/          The actual figures embedded in the manual
  specs.yaml       Every hardware fact the manual text depends on
  outline.md       Page-by-page structure (16 pages)
  content.md       Manual copy, in a light custom markup (see below)
  build.py         Orchestrator: content.md + specs.yaml -> HTML -> PDF/PNGs
  out/             Build output (gitignored)
```

## Illustrations: how they're made

The STLs are each oriented for 3D printing (see `models/PRINT_NOTES.md`), not
for the assembled product. `scripts/assembly.yaml` records, part by part, the
transform that rebuilds the real assembly, with a confidence note per part.

- **body, nose_cone, collar, foot** -- derived directly from the mesh
  geometry (joint rim radii, taper direction, the print-orientation notes).
  High confidence, not fitted_by_eye.
- **grille, bezel, knob, fins, LED** -- no CAD/generator source for these
  exists anywhere searched (this repo's full history, all branches, the
  upload set, the container filesystem) -- see the request thread. Per
  Ido's go-ahead, these are now fitted from two sources, in order of
  preference:
  1. **Witness marks already in body.stl.** Once a real bug in the
     hidden-line test was fixed (see `lineart.py`'s `visible_mask`
     docstring -- the occlusion ray was being cast away from the camera
     instead of toward it), the body mesh turned out to already carry the
     grille/bezel opening and its 4 mounting-screw pilot holes, the knob's
     mounting hole, and the fins' mounting pilot holes. `refit_from_mesh.py`
     finds these by clustering front-facing crease/silhouette edge points
     and fitting a circle to each cluster -- exact positions, not a guess.
  2. **The reference photo**, for whatever a witness mark doesn't cover:
     the fins' outward reach (mounting holes fix only the root), and the
     LED (no matching hole was found near it -- see the note on the `led`
     marker in `assembly.yaml`).
  Every part positioned this way is tagged `fitted_by_eye: true` in
  `assembly.yaml`, with a note on exactly what was used and why. The PDF
  build adds a "Provisional illustration" footer to every page that embeds
  one of these figures.

`scripts/lineart.py` then, for a given camera view:

1. Loads and transforms every part into one assembled scene.
2. Extracts **crease edges** (dihedral angle > 20 deg) and **silhouette
   edges** (edges where adjacent faces flip from facing the camera to
   facing away) plus open mesh boundaries.
3. Removes hidden lines with **true occlusion testing**: each candidate
   edge is sampled every 1.5 mm, and each sample point is ray-cast toward
   the camera against the full assembled mesh (`visible_mask`). A point is
   drawn only if nothing else in the assembly sits between it and the
   camera.
4. Projects the surviving segments orthographically and writes a plain
   black-line SVG, optionally with numbered callout leaders (`callouts=`)
   or cropped to a sub-region (`crop=`, used for the knob close-up).

The grille's honeycomb is simplified: edges shorter than 6 mm are dropped
for that part's internal detail lines only (never its outline -- an early
version of this filter also deleted the outer rim, since a tessellated
circle is made of many short segments too; fixed, see `feature_edges`'
docstring) so the drawing shows the grille's true outer boundary without
tracing every one of its ~1,700 hexagonal holes.

### Line weights

Set at final print size, not model size: `OUTLINE_WEIGHT_MM = 0.25` for the
visible profile, `DETAIL_WEIGHT_MM = 0.15` for internal feature lines.
`render_view` takes a `page_scale` that shrinks the drawing to fit a page
layout box *without* scaling the line weights. Checked at A6 page-fit scale
in `figures/test/test_front_confident_a6scale*` -- stays legible.

## content.md syntax

- `<!-- page: id -->` starts a new page (16 of these = 16 pages).
- `<!-- subtitle -->` on its own line, next line is the subtitle text.
- `<!-- figure: name [mod ...] -->` inlines `figures/final/name.svg`;
  modifiers (`small`, `centered`) add a CSS class.
- `{{spec:dotted.path}}` pulls a value from `specs.yaml`. If the value is
  `TBD_FROM_ODM` (or empty), it renders in bright magenta automatically --
  no need to mark it up separately, and it stops being magenta the moment
  a real value replaces `TBD_FROM_ODM` in `specs.yaml`.
- `{{page:id}}` resolves to another page's printed number, for cross-refs.
- `<!-- footer: provisional -->` adds the provisional-illustration footer
  note to that page (set automatically for pages using fitted_by_eye figures).
- Everything else is plain Markdown (tables via the `tables` extension).

## Rebuilding

```
python3 manual/build.py
```

Regenerating the figures themselves (if `assembly.yaml` changes):

```
python3 manual/scripts/make_figures.py
python3 manual/scripts/annotate_knob.py
python3 manual/build.py
```

Environment note: `render_pdf.js` and the various `svg2png` helpers used
during development hardcode this sandbox's Chromium/Playwright paths
(`/opt/pw-browsers/chromium`, `/opt/node22/lib/node_modules/playwright`).
On a different machine, point them at a local Playwright + Chromium install
instead.

## If the real assembly source turns up

Swapping in production CAD should only ever mean editing
`scripts/assembly.yaml` (and, if a part's own geometry changes, its STL in
`models/`) -- `lineart.py` reads every part's file and transform from that
one file, so no code changes are needed. Concretely: replace a `fitted_by_eye`
part's `rotate`/`translate` (or `matrix4`) with the real transform, drop the
`fitted_by_eye: true` flag, update its note, then re-run `make_figures.py`,
`annotate_knob.py` and `build.py`. The footer note disappears from a page
automatically once none of its figures are fitted_by_eye any more.
