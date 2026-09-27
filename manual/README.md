# Atelier manual

Printed instruction booklet for Atelier (Bathsheva London), A6, saddle-stitched.

## Status: Phase 1 (in review)

- [x] Page outline -- `outline.md`
- [x] Hardware spec placeholders -- `specs.yaml`
- [x] Illustration method chosen and test-rendered -- `scripts/lineart.py`
- [ ] Open decisions confirmed
- [ ] Phase 2: `content.md`, HTML/CSS layout, `build.py`, final PDF

## Folder layout

```
manual/
  models/         Source STLs (copied from the uploaded set) + PRINT_NOTES.md
  scripts/
    assembly.yaml   Per-part transforms that turn the print-oriented STLs
                     back into the real, right-way-up assembly
    lineart.py      Generates clean single-weight black line drawings
                     straight from the STL geometry, hidden lines removed
                     by real ray-cast occlusion testing (no shading, no AI)
  figures/
    test/           Phase 1 proof-of-concept renders (not final art)
  specs.yaml       Every hardware fact the manual text depends on
  outline.md       Proposed page-by-page structure
  content.md       (Phase 2) manual text, pulls facts from specs.yaml
  build.py         (Phase 2) one command: renders content.md + figures to
                     HTML, prints to manual/out/atelier-manual.pdf, plus a
                     PNG preview per page
```

## Illustrations: how they're made

The STLs are each oriented for 3D printing (see `models/PRINT_NOTES.md`), not
for the assembled product -- e.g. the body is modelled upside down so its
cone-joint rim sits flat on the print bed. `scripts/assembly.yaml` records,
part by part, the rotation and translation that undoes the print orientation
and rebuilds the real assembly, with a note on how confident each part's
placement is:

- **body, nose_cone, collar, foot** -- derived directly from the mesh
  geometry (joint rim radii, taper direction, the print-orientation notes).
  High confidence.
- **grille, bezel, knob, fins** -- positioned by estimate against the
  recess found in the body mesh and the reference photo. Flagged as
  estimates pending a closer fit -- see the open decisions list sent with
  Phase 1.

`scripts/lineart.py` then:

1. Loads and transforms every part into one assembled scene.
2. Extracts **crease edges** (dihedral angle > 20 deg) and **silhouette
   edges** (edges where adjacent faces flip from facing the camera to
   facing away) plus open mesh boundaries -- the standard feature set for a
   clean CAD-style line drawing.
3. Removes hidden lines with **true occlusion testing**: each candidate
   edge is sampled every 1.5 mm, and each sample point is ray-cast toward
   the camera against the full assembled mesh. A point is drawn only if
   nothing else in the assembly sits between it and the camera.
4. Projects the surviving segments orthographically and writes a plain
   black-line SVG.

The grille's honeycomb is deliberately simplified: edges shorter than 6 mm
are dropped for that part only, so the drawing shows the grille's true
outer boundary without tracing every one of its ~1,700 hexagonal holes
(which would look like a smudge at A6 size, not a clean line drawing).

Run it with:

```
cd manual && python3 scripts/lineart.py
```

Output lands in `figures/test/`. SVG -> PNG preview conversion used for
review (not part of the pipeline) was done with the Chromium install at
`/opt/pw-browsers/chromium` via Playwright.

## Rebuilding the manual (Phase 2)

```
python manual/build.py
```
