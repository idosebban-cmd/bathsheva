# ATELIER rocket speaker: build report

Generated 2026-09-23 08:35 by `python build.py` in 108 s. Split mode: **`nose_tail`**. Honeycomb grille: **on**.

## Overall dimensions

| | mm |
|---|---|
| Overall height (ground to nose tip) | 280.0 |
| Footprint across the fin tips (X x Y) | 138.5 x 131.1 |
| Body max diameter | 96.8 at 123.8 above ground |
| Body height (red) | 209.1 (from 25.8 to 234.8) |
| Nose cone height | 45.2 (22% of the body) |
| Body diameter at the cone joint / at the collar | 53.6 / 39.1 |
| Grille diameter / bezel OD / sound opening | 74.0 / 80.0 / 61.2 |
| Grille centre height | 162.1 |
| Knob centre / LED height | 97.4 / 114.2 |
| USB-C centre height, angle | 55.0, 150 deg from front |
| Fin tip distance from axis | 79.0 |

## Internal air volume

* **Body: 0.760 L**. That's the inner cavity minus the driver (57 x 30 mm), passive radiator (40 x 60 x 15 mm oval), battery, ballast cup, chassis, driver/radiator seats, spigots, and 31 cm3 of butyl pads.
* Nose cone interior: 0.031 L more, if the cone is left open to the body (total 0.791 L).
* For a sealed box, the knob shaft, LED and USB-C openings must be sealed.

## Assembly checks

* Driver (57 mm) goes in from the front through the 61.2 mm sound opening: OK
* Battery goes in through the 49.0 mm top (cone) opening (needs 41.6 mm): OK
* Top (nose cone) opening: 49.0 mm; bottom (collar) opening: 33.1 mm. Every internal part is sized to pass through one of them (the chassis is fitted as 4 pieces).
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
| body | pc_abs | 138.8 | 166.5 |
| nose_cone | aluminium | 12.1 | 32.8 |
| fin_1 | zinc_diecast | 16.2 | 107.0 |
| fin_2 | zinc_diecast | 16.2 | 107.0 |
| fin_3 | zinc_diecast | 16.2 | 107.0 |
| grille | stainless_304 | 2.6 | 20.5 |
| bezel | aluminium | 1.9 | 5.2 |
| knob | brass | 1.0 | 8.6 |
| vent_insert | stainless_304 | 0.8 | 6.1 |
| collar | zinc_diecast | 4.2 | 27.4 |
| foot | zinc_diecast | 1.8 | 11.6 |
| ballast | steel | 77.7 | 610.2 |
| chassis | steel | 13.1 | 102.8 |
| battery (bought-in) | - | - | 95.0 |
| driver (bought-in) | - | - | 65.0 |
| passive radiator (bought-in) | - | - | 40.0 |
| PCB (bought-in) | - | - | 30.0 |
| butyl damping pads | - | - | 50.0 |
| **Total** | | | **1592.7** |

* **Fins:** hollow die-cast with a 3 mm wall: **107.0 g each, 321.0 g for all 3** (solid would be 128.7 g each, 386.2 g).
* **Target: 1800 g. Total: 1592.7 g (-207.3 g).**
* **Ballast needed to hit the target: 817.5 g**; `BALLAST_MASS_G` is auto-sized to 610.2 g. The steel cup is 47.6 mm OD x 80.8 mm tall (top at 130.6 mm).

* **Centre of mass: 91.8 mm above the ground** (33% of overall height), offset 1.3 mm from the axis (towards the front grille and knob).
* Battery: 37 x 19 footprint, 65 tall, bottom at 49.8 mm, centre at 82.3 mm (the lowest position that fits and can be fitted through the 49.0 mm opening).

## Stability

* **Tips over at 21.2 deg of tilt** (worst direction, towards 0 deg, where 0 = front and 90 = right).
  * over the edge between fin tips 3 and 1 (towards 0 deg): 21.2 deg (CoM 35.6 mm inside that edge)
  * over the edge between fin tips 2 and 3 (towards 240 deg): 22.2 deg (CoM 37.5 mm inside that edge)
  * over the edge between fin tips 1 and 2 (towards 120 deg): 22.2 deg (CoM 37.5 mm inside that edge)
* How it's calculated: the rocket rests only on its three fin tips. Tilted about the line between two tips, it falls once the centre of mass passes over that line, so tip angle = atan(distance from CoM to the line / CoM height). For reference, the AV-equipment safety standard IEC 62368-1 tilts products by 10 deg in its stability test.
* The worst direction is towards the front, because the grille, bezel, knob and driver pull the CoM slightly forward, and a fin pair (not a single fin) faces that way.
* Mass low down: the 610 g steel ballast cup, the solid zinc foot and collar, and the battery all sit in the bottom third. The ballast adds mass, which makes the product feel solid and resist being nudged, but it only helps the tip angle as far as it lowers the CoM.

## Passive radiator

* **Fires down through the base** (the back stays smooth red). It's a round 44 mm radiator (35 mm radiating, **962 mm2**) on a flat seat moulded inside the body, 28.8 mm up. It's fitted through the cone opening.
* It breathes out through the body's bottom opening and the collar bore, then sideways through a **5.5 mm gap under the collar**. The gap reads as a dark shadow line, with a black mesh ring (60% open) recessed 1 mm behind it.

| Air path, in order | Area mm2 | x radiator area |
|---|---|---|
| body bottom opening | 691 | 0.72 |
| collar bore (narrowest) | 384 | 0.40 |
| vent mesh (open area) | 254 | 0.26 |
| outer slot under the collar | 468 | 0.49 |

* **Exit area: 254 mm2 = 0.26 x the radiator area** (limited by the vent mesh (open area)). The usual rule of thumb is at least 1 x. At this size the air moves several times faster than the radiator cone. Expect less bass from the radiator and possible 'chuffing' noise at high volume. That needs measuring on a prototype.
* Reaching 1 x through this gap alone would need a ~21 mm tall vent, which wouldn't read as a shadow line. Options: (a) a second hidden vent in the shadow line where the collar meets the body (at about 39 mm diameter, roughly doubling the mesh area); (b) widening the collar bore and dropping the mesh in favour of a plain slot; (c) the rear radiator (`PR_POSITION = "rear"`); (d) a sealed box without a radiator.
* The body sits **25.8 mm off the ground**, as in the concept.
* **Mass target not met:** at most 610.2 g of steel ballast fits below the driver, leaving the total 207.3 g short.

## Assembly steps that need a professional to resolve

The model proves the parts fit. These steps still need a mechanical or manufacturing engineer to resolve before tooling:

1. **Tool access to the fin bolts.** The six M4 bolts go radially from inside the body through the wall into the fins, with their heads on the fin brackets about 40 mm from the axis, at 61.4 and 80.9 mm up. A straight driver would come in along the bolt axis, from the centre of the body, which is where the ballast cup and battery sit. The only ways in are the end openings (33.1 mm at the bottom, 49.0 mm at the cone) and the driver hole (61.2 mm, well above). The brackets also bolt to the ballast cup, so the order of assembly is circular. Options: fit the fins and brackets before the ballast/battery using an offset or right-angle driver; use captive studs cast into the fins with nuts inside; or bolt the brackets to the cup with vertical screws reachable from the collar opening.
2. **Moulding the body.** A one-piece shell whose belly (95 mm) is much wider than its end openings can't be injection-moulded on a simple core. It needs a collapsible core, or two halves welded together (the seam disappears under the lacquer), and the internal driver and radiator seats may have to become separate parts. This decision affects the split strategy and the fitting sequence.
3. **Blind assembly and wiring.** The battery, ballast and radiator go in through a ~49 mm opening, and the knob encoder's nut sits about 40 mm below the driver hole. Connectors, service loops and special tools need defining, along with a repair/disassembly sequence.
4. **Retaining the nose cone and the base module.** Both locate on slip-fit spigots only. They need a hidden fastening (bayonet, screws into the chassis, or adhesive). Also check what carries the load when the product is lifted by the body.
5. **Acoustics.** Sealed-box air-tightness (knob shaft, LED, USB-C, seams, grille seats) and passive radiator tuning. The base radiator has about 26% less area than the rear oval, and its exit gap can be choked by soft surfaces such as a tablecloth, or collect dust. It needs measuring, not just calculating.
6. **Matching the gold finish across materials.** Anodised aluminium (cone, bezels), plated zinc (fins, foot), PVD stainless (grilles) and brass (knob) all have to match one gold. That means colour-matching between suppliers, plus lacquer build-up at mating faces and a consistent 0.4 mm shadow line at the cone joint.
7. **Die-cast fins.** Draft angles, core design, gate position and porosity (which matters under plating), and a gasket or pad at the fin/body interface so fin loads don't crack the lacquer.
8. **Safety and certification.** Heat from the battery and amplifier in a sealed, steel-lined enclosure, UN38.3 for the battery, and IEC 62368-1 (including the stability test).

## Parts and print orientation (output/stl)

| STL | Production material | Print orientation |
|---|---|---|
| body.stl | pc_abs | upside down, cone-joint rim on the bed |
| nose_cone.stl | aluminium | upright, spigot ring on the bed |
| fin_1.stl | zinc_diecast | lying on its side, tilted 0.0 deg so one tapered face is flat on the bed |
| fin_2.stl | zinc_diecast | lying on its side, tilted 0.0 deg so one tapered face is flat on the bed |
| fin_3.stl | zinc_diecast | lying on its side, tilted 0.0 deg so one tapered face is flat on the bed |
| grille.stl | stainless_304 | upright as fitted, standing on its lower edge |
| bezel.stl | aluminium | upright as fitted, standing on its lower edge |
| knob.stl | brass | front face down on the bed, shaft bore facing up |
| vent_insert.stl | stainless_304 | upright, plate on the bed |
| collar.stl | zinc_diecast | upside down, spigot on the bed |
| foot.stl | zinc_diecast | upside down, spigot on the bed |
| internal/ballast.stl | steel | internal production part (as assembled; printing is optional) |
| internal/chassis.stl | steel | internal production part (as assembled; printing is optional) |

