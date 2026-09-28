# Atelier manual

Printed instruction booklet for Atelier (Bathsheva London), A6, saddle-stitched, 16 pages.

## Status: Phase 2 draft built

```
python3 manual/build.py
```

rebuilds `manual/out/atelier-manual.pdf` plus one PNG preview per page,
`manual/out/tbd_report.txt` (every `TBD_FROM_ODM` value still in the PDF,
by occurrence AND by unique field -- a field like `power.charge_time_hours`
can appear on more than one page, so those two counts legitimately differ),
and `manual/out/legal_review_report.txt` (every sentence tagged `needs
ODM/compliance review` in `content.md` -- see below). `manual/out/` is
gitignored -- it's a build artifact, regenerate it rather than expecting it
to be checked in.

- [x] Page outline -- `outline.md` (16 pages, revised per review)
- [x] Hardware spec decisions -- `specs.yaml`
- [x] Illustrations -- `scripts/lineart.py` + `scripts/assembly.yaml`, see below
- [x] `content.md` -- the manual's copy, pulls every hardware fact from `specs.yaml`
- [x] `build.py` -- one command, HTML -> PDF + page PNGs, magenta TBD styling,
      thin magenta underline on every safety/battery/disposal/warranty/
      regulatory sentence, automatic overflow detection (fails the build
      rather than silently clipping a page)
- [x] Grille/bezel/knob/LED positions -- mesh-derived from real openings on
      body.stl's front face (see below), not fitted. A ~19mm gap between
      the knob and the grille/bezel, LED in between: matches the reference
      photo and Ido's own independent measurement of body.stl.
- [ ] Real CAD source for the grille/bezel/knob/fin part GEOMETRY itself
      (their shape, not position) -- still not found; those STLs remain
      unverified, and the fins' outward reach is still photo-fitted

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
    find_front_holes.py Ray-casts body.stl's front centreline to find every
                          real opening -- the current, verified source for
                          grille/bezel/knob/LED position (see below)
    refit_from_mesh.py  Vertex-cluster method; superseded for grille/bezel/
                          knob by find_front_holes.py (it misidentified the
                          knob once, see below) but still used for the fins'
                          mounting-hole root
    measure_knob_gap.py Measures the real knob-to-bezel gap from mesh bounds
    photo_fit.py        Original photo-pixel-based fitting; only the fin
                          tip / footprint radius still comes from this
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
- **grille, bezel, knob, LED** -- no CAD/generator source for these parts'
  own GEOMETRY exists anywhere searched (this repo's full history, all
  branches, the upload set, the container filesystem), but their POSITION
  is mesh-derived, not fitted: `scripts/find_front_holes.py` ray-casts
  along body.stl's front centreline (from far +Y toward -Y) and records
  every stretch where the front face has no material -- i.e. every real
  opening, found directly from the triangulated surface. That gives exact
  centres for the grille/bezel opening, the LED hole and the knob hole (see
  `assembly.yaml`'s notes on each part for the numbers). Not tagged
  `fitted_by_eye`.

  An earlier pass (`refit_from_mesh.py`'s vertex-cluster method, still used
  for the fins below) misidentified the knob's position: a noisy cluster at
  file_z ~101-110 with a much higher std (4.6-5.0) than every genuine hole
  found the same way (LED: std 0.01, bezel screws: std 0.19-0.40) turned
  out to be boundary artefacts from the grille recess's own edge, not a
  hole at all. Ido caught this by independently measuring body.stl himself
  and got a different number; re-deriving with the more rigorous ray-cast
  sweep confirmed his measurement (all three centres within a fraction of a
  mm) and found the real knob hole 30mm further round the taper. Worth
  learning from: the cluster method's own std/quality signal already showed
  the first answer was suspect, and that should have been caught before
  reporting it rather than after.
- **fins** -- root mesh-derived (mounting pilot holes, same
  `refit_from_mesh.py` cluster method, clean low-std holes so no reason to
  doubt these), tip photo-derived (no matching witness mark for how far out
  the fin reaches -- mounting holes fix only the root). Tagged
  `fitted_by_eye: true`; the PDF build adds a "Provisional illustration"
  footer to every page whose figure includes the fins (front_callouts,
  hero_front). knob_closeup and underside_callouts don't include them, so
  they carry no such footer.

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

### Knob/grille/LED derivation, and the gap between them

`scripts/find_front_holes.py`'s centreline sweep of body.stl gives:

| Feature | file_z range | centre (file_z) | world_z |
|---|---|---|---|
| grille/bezel opening | 48.5 - 97.5 | 73.0 | 136.1 |
| LED hole (dia. ~2mm) | 119.5 - 122.5 | 121.0 | 88.1 |
| knob hole (dia. ~10mm) | 132.5 - 143.0 | 137.75 | 71.35 |

All three match Ido's own independent measurement of body.stl to within a
fraction of a mm (his: grille 73, LED 121, knob 137.5). `scripts/
measure_knob_gap.py` reports the resulting gap between the knob and the
grille/bezel, using the parts' real mesh bounds at these positions: **+18.9mm**
to the grille's bottom edge, +15.9mm to the bezel's (the bezel's own mesh
extends slightly further down than the grille's) -- a real gap, not an
overlap, with the LED sitting inside it. Matches the reference photo's
composition and Ido's own estimate of "about 20mm".

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
- The provisional-illustration footer is set **automatically** whenever a
  page embeds a figure built from fitted_by_eye geometry (see
  `FITTED_FIGURES` in `build.py`) -- don't add it by hand, that's how it
  ended up on text-only pages like Charging in an earlier draft. A manual
  `<!-- footer: provisional -->` override still works if a future figure
  needs one without being in `FITTED_FIGURES`, but nothing in `content.md`
  currently uses it.
- `<span class="legal" title="needs ODM/compliance review">...</span>`
  wraps one sentence of safety, battery, disposal, warranty or regulatory
  wording. Renders with a thin magenta underline in the PDF (distinct from
  `.tbd`'s solid magenta fill, so a TBD value inside a flagged sentence
  shows both markers at once, not one masking the other). Every build lists
  them in `manual/out/legal_review_report.txt`.
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
