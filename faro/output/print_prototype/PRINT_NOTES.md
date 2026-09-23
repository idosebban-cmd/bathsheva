# Faro looks-like prototype: print notes

Faro lighthouse lamp, Rosso. 300.5 mm tall on its felt pad. The STLs here are turned to their print orientation and sit on the bed at z = 0 (mm). `faro/output/stl/` has the same parts as assembled.

## Parts to print

| File | Qty | Material | Orientation | Supports? | Size X x Y x Z | Notes |
|---|---|---|---|---|---|---|
| base_plate.stl | 1 | PLA+ or PETG, black | felt recess up (flat top face on the bed) | No | 109 x 109 x 3 | Glue the 4 magnets into their pockets, flush with the recess floor |
| base.stl | 1 | PLA+ (wood-fill PLA, or paint walnut) | upright, open underside on the bed | Yes: tree supports inside the battery bay only (hidden), under the bay ceiling and bosses | 113 x 113 x 27 | Production: CNC-turned walnut with M3 threaded inserts in the bosses. For the prototype, melt M3 heat-set inserts into the bosses |
| nameplate.stl | 1 | Resin, or PLA+ painted brass | outer face (lettering) up | Yes: supports under the curved back (the plate arches about 3 mm) | 37 x 11 x 5 | Glue into the recess on the base front. Production: etched or engraved brass |
| band_cream.stl | 1 | PLA+ or PETG | upright | No | 97 x 97 x 6 | Paint cream lacquer; glue onto the base top |
| band_red.stl | 1 | PLA+ or PETG | upright, wide end down | No | 92 x 92 x 36 | Paint red lacquer |
| tower.stl | 1 | PLA+ or PETG | upright, wide end down | No: the window arches are self-supporting | 86 x 86 x 128 | Paint cream lacquer (mask the window edges) |
| window_diffuser_x2.stl | 2 | Translucent resin, sanded | front face up | Yes, on the inner face only | 16 x 25 x 2 | Or cut from 1 mm opal polycarbonate. Glue behind each window |
| knob.stl | 1 | Resin or PLA+ | front face down | No | 20 x 20 x 7 | Brass paint; glue on, or fit on a 6 mm shaft |
| gallery.stl | 1 | Resin recommended (PLA+ with a 0.2 mm nozzle) | upright, platform on the bed | No: posts are vertical; the rails bridge about 17 mm between posts | 90 x 90 x 24 | 1.6 mm posts and rails. Brass paint or brass-fill filament |
| lantern_frame.stl | 1 | Resin recommended | upright, bottom ring on the bed | No: the bayonet lip overhangs only 1.8 mm | 55 x 55 x 41 | Check the cap twists on before painting |
| lantern_glass.stl | 1 | Translucent PETG or clear resin, sanded/frosted | upright | No | 50 x 50 x 35 | Stands on the gallery platform; the frame is lowered over it |
| cap.stl | 1 | PLA+ or resin | upright, spigot on the bed | Yes: under the rim (build-plate only); the lugs need none | 71 x 71 x 43 | Paint red lacquer. Twist on: drop the lugs through the slots, turn clockwise to the stop |
| finial.stl | 1 | Resin, or PLA+ painted brass | upright, neck on the bed | Yes, light supports under the ball | 14 x 14 x 16 | Glue into the cap's collar |

## Not printed

| Part | How it's made |
|---|---|
| felt_pad (felt_pad_REFERENCE_ONLY.stl) | Cut from 1.5 mm felt laminated to a 0.4 mm steel disc (self-adhesive felt on steel shim works). The STL is only a size reference |

## Render-only / bought-in (not in the print set)

| Item | What to use |
|---|---|
| Battery | 65 x 37 x 19 mm 2 x 18650 pack (placeholder) |
| LED module | Ø20 x 12 mm (placeholder) |
| USB-C receptacle | board-mounted, behind the rear port (placeholder) |
| Screws | 4 x M3 x 8 countersunk, hex socket |
| Threaded inserts | 4 x M3 heat-set inserts for the base bosses |
| Magnets | 4 x Ø6 x 1.5 mm N52 discs |

## Assembly order

1. Base: melt the 4 M3 inserts into the bosses; glue on the nameplate.
2. Glue the cream band onto the base top, then the red band, then the tower, all centred (they stack on flat joints). Glue the knob and the window diffusers.
3. Glue the gallery onto the tower top. Stand the lantern glass on the gallery platform, then lower the frame over it and glue the frame to the gallery.
4. Glue the finial into the cap. Twist the cap on: lugs down through the 4 slots, turn 20 deg clockwise (seen from above) to the stop.
5. Underneath: battery in the bay, plate on with the 4 screws, felt pad on (the magnets hold it).

## Fit checks (from the model)

* Battery bay 105 mm across x 20.5 mm tall: the battery has 1.0 mm headroom and clears the screw bosses.
* Walnut under the rounded top edge: at least 2.8 mm.
* Cap bayonet: no clash when locked (0.00 mm3), lugs pass the slots at entry (0.00 mm3), 1.6 mm of lug under the lip. With the cap off the opening is Ø49 mm, so the Ø20 mm LED module lifts out.
* Fit clearance 0.2 mm per side on the bayonet and 0.2 mm round the bottom plate: PLA may need light sanding.
* The felt stands 0.5 mm proud of the walnut, so the lamp sits on the felt, not the wood.

## General

* Widest part: base.stl at 113 mm; tallest: tower.stl at 128 mm. Any common printer (180 x 180 x 180 mm or more) fits every part.
* Paint the lacquer parts with filler-primer, sanding, then gloss cream / red and a clear coat. Brass parts: metallic gold over gloss black, or brass-fill filament polished.
* The railing and lantern frame are the most delicate parts; resin gives the crispest result.

