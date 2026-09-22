# ATELIER rocket speaker: build report

Generated 2026-09-22 20:53 by `python build.py` in 44 s. Split mode: **`nose_tail`**. Honeycomb grille: **off (plain disc)**.

## Overall dimensions

| | mm |
|---|---|
| Overall height (ground to nose tip) | 280.0 |
| Footprint across the fin tips (X x Y) | 141.1 x 131.8 |
| Body max diameter | 95.0 at 114.8 above ground |
| Body height (red) | 214.6 (from 18.2 to 232.8) |
| Nose cone height | 47.2 (22% of the body) |
| Body diameter at the cone joint / at the collar | 58.9 / 52.3 |
| Grille diameter / bezel OD / sound opening | 65.4 / 73.4 / 60.4 |
| Grille centre height | 151.2 |
| Knob centre / LED height | 87.3 / 105.4 |
| USB-C centre height, angle | 48.2, 150 deg from front |
| Fin tip distance from axis | 80.8 |

## Internal air volume

* **Body: 0.775 L**. That's the inner cavity minus the driver (57 x 30 mm), passive radiator (40 x 60 x 15 mm oval), battery, ballast cup, chassis, driver/radiator seats, spigots, and 31 cm3 of butyl pads.
* Nose cone interior: 0.033 L more, if the cone is left open to the body (total 0.809 L).
* For a sealed box, the knob shaft, LED and USB-C openings must be sealed.

## Assembly checks

* Driver (57 mm) goes in from the front through the 60.4 mm sound opening: OK
* Battery goes in through the 47.8 mm bottom opening (needs 41.6 mm): OK
* Top (nose cone) opening: 54.3 mm; bottom (collar) opening: 47.8 mm. Every internal part is sized to pass through one of them (the chassis is fitted as 4 pieces).
* Fin brackets reach the ballast cup to bolt to it: OK
* Driver vs battery: OK
* Driver vs passive radiator: OK
* Driver vs chassis: OK
* Driver vs ballast: OK
* Battery vs passive radiator: OK
* Battery vs chassis: OK
* Battery vs ballast: OK
* Passive radiator vs chassis: OK
* Passive radiator vs ballast: OK
* Chassis vs ballast: OK

## Mass and centre of mass (production materials)

| Part | Material | Volume cm3 | Mass g |
|---|---|---|---|
| body | pc_abs | 141.5 | 169.8 |
| nose_cone | aluminium | 12.9 | 34.9 |
| fin_1 | zinc_diecast | 17.4 | 114.5 |
| fin_2 | zinc_diecast | 17.4 | 114.5 |
| fin_3 | zinc_diecast | 17.4 | 114.5 |
| foot | zinc_diecast | 31.5 | 207.6 |
| grille | stainless_304 | 4.3 | 34.8 |
| bezel | aluminium | 3.1 | 8.4 |
| knob | brass | 1.0 | 8.9 |
| ballast | steel | 74.0 | 581.0 |
| chassis | steel | 14.2 | 111.4 |
| battery (bought-in) | - | - | 95.0 |
| driver (bought-in) | - | - | 65.0 |
| passive radiator (bought-in) | - | - | 60.0 |
| PCB (bought-in) | - | - | 30.0 |
| butyl damping pads | - | - | 50.0 |
| **Total** | | | **1800.3** |

* **Fins:** hollow die-cast with a 3 mm wall: **114.5 g each, 343.5 g for all 3** (solid would be 206.1 g each, 618.4 g).
* **Target: 1800 g. Total: 1800.3 g (+0.3 g).**
* **Ballast needed to hit the target: 580.7 g**; `BALLAST_MASS_G` is set to 581.0 g. The steel cup is 46.4 mm OD x 84.6 mm tall (top at 108.8 mm).

* **Centre of mass: 79.2 mm above the ground** (28% of overall height), offset 0.7 mm from the axis (towards the front grille and knob).
* Battery: 37 x 19 footprint, 65 tall, bottom at 24.2 mm, centre at 56.7 mm (the lowest position that fits and can be fitted through the 47.8 mm opening).

## Stability

* **Tips over at 25.2 deg of tilt** (worst direction, towards 0 deg, where 0 = front and 90 = right).
  * over the edge between fin tips 3 and 1 (towards 0 deg): 25.2 deg (CoM 37.3 mm inside that edge)
  * over the edge between fin tips 2 and 3 (towards 240 deg): 25.8 deg (CoM 38.4 mm inside that edge)
  * over the edge between fin tips 1 and 2 (towards 120 deg): 25.8 deg (CoM 38.4 mm inside that edge)
* How it's calculated: the rocket rests only on its three fin tips. Tilted about the line between two tips, it falls once the centre of mass passes over that line, so tip angle = atan(distance from CoM to the line / CoM height). For reference, the AV-equipment safety standard IEC 62368-1 tilts products by 10 deg in its stability test.
* The worst direction is towards the front, because the grille, bezel, knob and driver pull the CoM slightly forward, and a fin pair (not a single fin) faces that way.
* Mass low down: the 581 g steel ballast cup, the solid zinc foot and collar, and the battery all sit in the bottom third. The ballast adds mass, which makes the product feel solid and resist being nudged, but it only helps the tip angle as far as it lowers the CoM.

## Parts and print orientation (output/stl)

| STL | Production material | Print orientation |
|---|---|---|
| body.stl | pc_abs | upside down, top rim on the bed (walls self-supporting) |
| nose_cone.stl | aluminium | upright, spigot ring on the bed |
| fin_1.stl | zinc_diecast | lying flat on its side (tapered faces need light support or a brim) |
| fin_2.stl | zinc_diecast | lying flat on its side (tapered faces need light support or a brim) |
| fin_3.stl | zinc_diecast | lying flat on its side (tapered faces need light support or a brim) |
| foot.stl | zinc_diecast | upside down, spigot on the bed |
| grille.stl | stainless_304 | front face up (curved, like a shallow dome) |
| bezel.stl | aluminium | front face up (curved, like a shallow dome) |
| knob.stl | brass | front face down on the bed, shaft bore facing up |
| internal/ballast.stl | steel | internal production part (as assembled; printing is optional) |
| internal/chassis.stl | steel | internal production part (as assembled; printing is optional) |

