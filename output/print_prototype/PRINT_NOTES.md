# ATELIER looks-like prototype: print notes

Visible parts only: the fins are solid and there are no internals. The STLs are already turned to the print orientation below and sit on the bed at z = 0. Units are mm.

| File | Qty | Material | Orientation | Supports? | Size X x Y x Z | Notes |
|---|---|---|---|---|---|---|
| body.stl | 1 | PLA+ or PETG | upside down, cone-joint rim on the bed | No. Walls lean less than 30 deg; small holes bridge | 97 x 97 x 209 | 0.12-0.16 mm layers; 3-4 walls; 15% infill. Sand, filler-prime, then automotive red and 2K clear coat for the lacquer look |
| nose_cone.stl | 1 | PLA+ | upright, spigot ring on the bed | No | 53 x 53 x 52 | 0.12 mm layers for a smooth cone; gold paint or gold PLA |
| fin_x3.stl | 3 | PLA+ or PETG | lying on its side, tilted 0.0 deg so one tapered face is flat on the bed | No (use a brim for adhesion) | 54 x 88 x 8 | Solid in this version. 30-40% infill adds some weight. The 3.3 mm pilot holes take M4 self-tapping screws from inside, or glue with epoxy |
| grille.stl | 1 | Resin (SLA/MSLA) recommended | upright as fitted, standing on its lower edge | Yes, build-plate-only supports under the lower third of the edge | 66 x 19 x 74 | Print version: 2.2 mm honeycomb with 1 mm webs (production is 0.7 mm, photo-etched stainless). Glue into the recess; paint the recess floor matt black first |
| bezel.stl | 1 | Resin or PLA+ | upright as fitted, standing on its lower edge | Yes, build-plate-only supports under the lower third of the edge | 70 x 23 x 80 | Glue into the recess over the grille edge |
| knob.stl | 1 | Resin or PLA+ | front face down on the bed, shaft bore facing up | No | 18 x 18 x 7 | Press-fits on a 6 mm shaft; for a mock-up, glue a short 6 mm dowel |
| collar.stl | 1 | PLA+ | upside down, spigot on the bed | No: the cup and the port recess lean less than 45 deg | 50 x 50 x 20 | Friction-fits into the body (0.2 mm clearance); sand to fit. Includes the USB-C port recess, receptacle pocket and wire channel |
| foot.stl | 1 | PLA+ | upside down, flat top on the bed | No | 18 x 18 x 10 | The small rounded knob: glue it centred under the collar cup |

## General

* **Printer size:** the largest part is body.stl at 97 x 97 x 209 mm, so you need at least 214 mm of build height (a Bambu X1/P1 or Prusa MK4/XL fits).
* Print a test fit of the cone and foot spigots first. Fit clearance is 0.2 mm per side, so PLA may need light sanding.
* Paint the body before fitting anything. The gold parts look best in metallic gold paint over a gloss black base, or in silk gold PLA.
* Honeycomb grilles: on FDM, set the slicer's 'detect thin walls' on, or print them in resin.
* **Weight and stability:** the printed prototype weighs about 177 g (PLA at ~60% density), with its centre of mass at 101 mm and a tip-over angle of about 20 deg. The production unit is 1.8 kg. For a realistic feel, glue about 500 g of steel shot or fishing weights low inside the body.

