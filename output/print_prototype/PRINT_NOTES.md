# ATELIER looks-like prototype: print notes

Visible parts only: the fins are solid and there are no internals. The STLs are already turned to the print orientation below and sit on the bed at z = 0. Units are mm.

| File | Qty | Material | Orientation | Supports? | Size X x Y x Z | Notes |
|---|---|---|---|---|---|---|
| body.stl | 1 | PLA+ or PETG | upside down, cone-joint rim on the bed | No. Walls lean less than 30 deg; small holes bridge | 95 x 95 x 207 | 0.12-0.16 mm layers; 3-4 walls; 15% infill. Sand, filler-prime, then automotive red and 2K clear coat for the lacquer look |
| nose_cone.stl | 1 | PLA+ | upright, spigot ring on the bed | No | 59 x 59 x 53 | 0.12 mm layers for a smooth cone; gold paint or gold PLA |
| fin_x3.stl | 3 | PLA+ or PETG | lying on its side, tilted 7.7 deg so one tapered face is flat on the bed | No (use a brim for adhesion) | 51 x 100 x 21 | Solid in this version. 30-40% infill adds some weight. The 3.3 mm pilot holes take M4 self-tapping screws from inside, or glue with epoxy |
| foot.stl | 1 | PLA+ | upright, foot stub on the bed | Yes, under the collar ring (it overhangs the posts by about 9 mm) | 52 x 52 x 31 | Friction-fits into the body (0.2 mm clearance); sand to fit |
| grille.stl | 1 | Resin (SLA/MSLA) recommended | upright as fitted, standing on its lower edge | Yes, build-plate-only supports under the lower third of the edge | 65 x 16 x 65 | The 2.2 mm honeycomb with 0.7 mm webs is at the limit of FDM (needs a 0.2 mm nozzle). Glue into the recess |
| bezel.stl | 1 | Resin or PLA+ | upright as fitted, standing on its lower edge | Yes, build-plate-only supports under the lower third of the edge | 73 x 23 x 73 | Glue into the recess over the grille edge |
| knob.stl | 1 | Resin or PLA+ | front face down on the bed, shaft bore facing up | No | 18 x 18 x 7 | Press-fits on a 6 mm shaft; for a mock-up, glue a short 6 mm dowel |

## General

* **Printer size:** the largest part is body.stl at 95 x 95 x 207 mm, so you need at least 212 mm of build height (a Bambu X1/P1 or Prusa MK4/XL fits).
* Print a test fit of the cone and foot spigots first. Fit clearance is 0.2 mm per side, so PLA may need light sanding.
* Paint the body before fitting anything. The gold parts look best in metallic gold paint over a gloss black base, or in silk gold PLA.
* Honeycomb grilles: on FDM, set the slicer's 'detect thin walls' on, or print them in resin.
* **Weight and stability:** the printed prototype weighs about 197 g (PLA at ~60% density), with its centre of mass at 100 mm and a tip-over angle of about 21 deg. The production unit is 1.8 kg. For a realistic feel, glue about 500 g of steel shot or fishing weights low inside the body.

