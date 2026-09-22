# ATELIER rocket speaker: build report

Generated 2026-09-22 20:07 by `python build.py` in 15 s. Split mode: **`nose_tail`**. Honeycomb grille: **off (plain disc)**.

## Overall dimensions

| | mm |
|---|---|
| Overall height (ground to nose tip) | 280.0 |
| Footprint across the fin tips (X x Y) | 140.7 x 137.0 |
| Body max diameter | 95.0 at 119.2 above ground |
| Body height (red) | 208.9 (from 25.2 to 234.1) |
| Nose cone height | 45.9 (22% of the body) |
| Body diameter at the cone joint / at the collar | 54.1 / 52.3 |
| Grille diameter / bezel OD / sound opening | 63.8 / 71.8 / 58.8 |
| Grille centre height | 154.7 |
| Knob centre / LED height | 92.1 / 109.9 |
| USB-C centre height, angle | 54.4, 150 deg from front |
| Fin tip distance from axis | 80.8 |

## Internal air volume

* **Body: 0.849 L** (the inner cavity minus the driver envelope (57 x 30 mm), the battery envelope, the driver mount and the spigots).
* Nose cone interior: 0.028 L more, if the cone is left open to the body (total 0.877 L).
* For a sealed box, the knob shaft, LED and USB-C openings must be sealed.

## Assembly checks

* Driver (57 mm) goes in from the front through the 58.8 mm sound opening: OK
* Battery goes in through the 47.9 mm bottom opening (needs 41.6 mm): OK
* Top (nose cone) opening: 49.4 mm; bottom (collar) opening: 47.9 mm. Both are for PCBs, wiring, battery and knob/LED boards.

## Mass and centre of mass (production materials)

| Part | Material | Volume cm3 | Mass g |
|---|---|---|---|
| body | pc_abs | 133.1 | 159.8 |
| nose_cone | aluminium | 11.6 | 31.4 |
| fin_1 | zinc_diecast | 16.6 | 109.7 |
| fin_2 | zinc_diecast | 16.6 | 109.7 |
| fin_3 | zinc_diecast | 16.6 | 109.7 |
| foot | zinc_diecast | 31.6 | 208.7 |
| grille | aluminium | 4.1 | 11.2 |
| bezel | aluminium | 3.0 | 8.0 |
| knob | aluminium | 2.0 | 5.4 |
| battery (bought-in) | - | - | 95.0 |
| driver (bought-in) | - | - | 65.0 |
| PCB (bought-in) | - | - | 30.0 |
| **Total** | | | **943.6** |

* **Centre of mass: 76.4 mm above the ground** (27% of overall height), offset 2.1 mm from the axis (towards the front grille and knob).
* Battery: 37 x 19 footprint, 65 tall, bottom at 31.2 mm, centre at 63.7 mm (the lowest position that fits).

## Stability

* **Tips over at 25.9 deg of tilt** (worst direction, towards 0 deg, where 0 = front and 90 = right).
  * over the edge between fin tips 3 and 1 (towards 0 deg): 25.9 deg (CoM 37.0 mm inside that edge)
  * over the edge between fin tips 1 and 2 (towards 120 deg): 27.7 deg (CoM 40.2 mm inside that edge)
  * over the edge between fin tips 2 and 3 (towards 240 deg): 27.7 deg (CoM 40.2 mm inside that edge)
* How it's calculated: the rocket rests only on its three fin tips. Tilted about the line between two tips, it falls once the centre of mass passes over that line, so tip angle = atan(distance from CoM to the line / CoM height). For reference, the AV-equipment safety standard IEC 62368-1 tilts products by 10 deg in its stability test.
* The worst direction is towards the front, because the grille, bezel, knob and driver pull the CoM slightly forward, and a fin pair (not a single fin) faces that way. The solid zinc foot and collar act as ballast.

## Parts and print orientation (output/stl)

| STL | Production material | Print orientation |
|---|---|---|
| body.stl | pc_abs | upside down, top rim on the bed (walls self-supporting) |
| nose_cone.stl | aluminium | upright, spigot ring on the bed |
| fin_1.stl | zinc_diecast | lying flat on its side (tapered faces need light support or a brim) |
| fin_2.stl | zinc_diecast | lying flat on its side (tapered faces need light support or a brim) |
| fin_3.stl | zinc_diecast | lying flat on its side (tapered faces need light support or a brim) |
| foot.stl | zinc_diecast | upside down, spigot on the bed |
| grille.stl | aluminium | front face up (curved, like a shallow dome) |
| bezel.stl | aluminium | front face up (curved, like a shallow dome) |
| knob.stl | aluminium | front face down on the bed, shaft bore facing up |

