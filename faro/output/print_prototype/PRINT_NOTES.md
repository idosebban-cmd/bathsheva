# Faro looks-like prototype: print notes

Faro lighthouse lamp, Rosso. 300.8 mm tall on its felt pad. The STLs here are turned to their print orientation and sit on the bed at z = 0 (mm). `faro/output/stl/` has the same parts as assembled.

## Parts to print

| File | Qty | Material | Orientation | Supports? | Size X x Y x Z | Notes |
|---|---|---|---|---|---|---|
| base_plate.stl | 1 | PLA+ or PETG, black | felt recess up (flat top face on the bed) | No | 109 x 109 x 3 | A plain plate: glue it into the rebate under the base; the felt sticks into its shallow recess |
| base.stl | 1 | PLA+ (wood-fill PLA, or paint walnut) | upright, open underside on the bed | Yes: tree supports inside the hollow base only (hidden), under its ceiling | 113 x 113 x 27 | Sponged burnt umber for the walnut effect. The fairy lights come in through the rear port |
| nameplate.stl | 1 | Resin, or PLA+ painted brass | outer face (lettering) up | Yes: supports under the curved back (the plate arches about 3 mm) | 37 x 11 x 5 | Glue into the recess on the base front. Production: etched or engraved brass |
| band_cream.stl | 1 | PLA+ or PETG | upright | No | 97 x 97 x 6 | Paint cream lacquer; glue onto the base top |
| band_red.stl | 1 | PLA+ or PETG | upright, wide end down | No | 92 x 92 x 36 | Paint red lacquer |
| tower.stl | 1 | PLA+ or PETG | upright, wide end down | No: the window arches are self-supporting | 86 x 86 x 128 | Paint cream lacquer (mask the window edges) |
| window_diffuser_1.stl | 1 | Translucent resin, sanded | outer face up | Yes, on the inner face only | 16 x 25 x 4 | One per window, numbered from the lowest (front) up; each follows the tower's taper at its own height, so keep them in order. Or cut from 1 mm opal polycarbonate. Glue behind its window |
| window_diffuser_2.stl | 1 | Translucent resin, sanded | outer face up | Yes, on the inner face only | 16 x 25 x 4 | As window_diffuser_1; goes behind the right side window |
| window_diffuser_3.stl | 1 | Translucent resin, sanded | outer face up | Yes, on the inner face only | 16 x 25 x 4 | As window_diffuser_1; goes behind the rear window |
| window_diffuser_4.stl | 1 | Translucent resin, sanded | outer face up | Yes, on the inner face only | 16 x 25 x 4 | As window_diffuser_1; goes behind the left side window |
| window_diffuser_5.stl | 1 | Translucent resin, sanded | outer face up | Yes, on the inner face only | 16 x 25 x 4 | As window_diffuser_1; goes behind the front window |
| knob.stl | 1 | Resin or PLA+ | front face down | No | 20 x 20 x 7 | Brass paint; glue on, or fit on a 6 mm shaft |
| gallery.stl | 1 | Resin recommended (PLA+ with a 0.2 mm nozzle) | upright, platform on the bed | No: posts are vertical; the rails bridge about 17 mm between posts | 90 x 90 x 24 | 1.6 mm posts and rails. Brass paint or brass-fill filament |
| lantern_frame.stl | 1 | Resin recommended | upright, bottom ring on the bed | No: the bayonet lip overhangs only 1.8 mm | 55 x 55 x 41 | Check the cap twists on before painting |
| lantern_glass.stl | 1 | Translucent PETG or clear resin, sanded/frosted | upright | No | 50 x 50 x 35 | Stands on the gallery platform; the frame is lowered over it |
| cap.stl | 1 | PLA+ or resin | upright, spigot on the bed | Yes: under the rim (build-plate only); the lugs need none | 71 x 71 x 43 | Paint red lacquer. Twist on: drop the lugs through the slots, turn clockwise to the stop |
| finial.stl | 1 | Resin, or PLA+ painted brass | upright, neck on the bed | Yes, light supports under the ball | 14 x 14 x 16 | Glue into the cap's collar |

## Not printed

| Part | How it's made |
|---|---|
| felt_pad (felt_pad_REFERENCE_ONLY.stl) | Cut from black self-adhesive felt, trimmed to size, and stuck on. The STL is only a size reference |

## Render-only / bought-in (not in the print set)

| Item | What to use |
|---|---|
| Fairy lights | Warm white copper fairy lights with a 3 x AA battery box (the box stays outside, behind the lamp) |
| LED puck | Rechargeable warm white LED puck, under 45 mm across, for the brightness test (it rests on the ledge inside the gallery) |
| Coins | A few coins, taped low inside the base, for weight |
| Epoxy | Araldite Rapid, with cocktail sticks |

## Assembly order

See the build manual (faro/output/manual/Faro_Build_Manual.pdf) for painting and finishing.
1. Diffusers into the tower. Through the open top, glue each behind its window with tiny dabs at the edges only (1 = lowest, on the front, up to 5 = highest, back on the front).
2. Nameplate into its recess on the front of the base.
3. Knob onto the front of the red band, centred.
4. Thread the lights in through the USB-C port at the back of the base and up through the hole in its top. The battery box stays outside, behind the lamp.
5. Stack and glue the cream band onto the base, then the red band, then the tower, with knob and nameplate aligned. Pull the lights up as you go.
6. Coil the lights loosely inside the tower so some sit near each window. Keep them all in the tower.
7. Gallery onto the tower top.
8. Lantern. Stand the empty glass on the gallery, lower the frame over it and glue the frame to the gallery. The lantern stays empty for the brightness test.
9. Finial into the cap, then twist the cap on: lugs down through the 4 slots, turn 20 deg clockwise (seen from above) to the stop. Do not glue it.
10. Weight. Tape a few coins low inside the base.
11. Underneath. Glue the base plate into its rebate, then apply the felt, trimmed to size. No inserts, screws or magnets in the prototype.

## Fit checks (from the model)

* Hollow base 105 mm across x 20.5 mm tall: room for the coins, and for the fairy-light wire from the rear port to the hole in the top.
* LED puck: a ledge inside the gallery leaves a Ø34 mm hole, so a puck up to 45 mm rests at lantern height on 5.5 mm of ledge.
* Walnut under the rounded top edge: at least 2.8 mm.
* Cap bayonet: no clash when locked (0.00 mm3), lugs pass the slots at entry (0.00 mm3), 1.6 mm of lug under the lip. With the cap off the opening is Ø49 mm, so the Ø20 mm LED module lifts out.
* Fit clearance 0.2 mm per side on the bayonet and 0.2 mm round the bottom plate: PLA may need light sanding.
* The felt stands 0.8 mm proud of the walnut, so the lamp sits on the felt, not the wood.

## General

* Widest part: base.stl at 113 mm; tallest: tower.stl at 128 mm. Any common printer (180 x 180 x 180 mm or more) fits every part.
* Paint the lacquer parts with filler-primer, sanding, then gloss cream / red and a clear coat. Brass parts: metallic gold over gloss black, or brass-fill filament polished.
* The railing and lantern frame are the most delicate parts; resin gives the crispest result.

