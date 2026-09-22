# ATELIER rocket speaker: build report

Generated 2026-09-22 21:21 by `python build.py` in 97 s. Split mode: **`nose_tail`**. Honeycomb grille: **on**.

## Overall dimensions

| | mm |
|---|---|
| Overall height (ground to nose tip) | 280.0 |
| Footprint across the fin tips (X x Y) | 141.2 x 131.7 |
| Body max diameter | 95.0 at 120.6 above ground |
| Body height (red) | 207.0 (from 27.4 to 234.5) |
| Nose cone height | 45.5 (22% of the body) |
| Body diameter at the cone joint / at the collar | 58.9 / 52.3 |
| Grille diameter / bezel OD / sound opening | 65.4 / 73.4 / 60.4 |
| Grille centre height | 155.8 |
| Knob centre / LED height | 92.5 / 110.3 |
| USB-C centre height, angle | 56.4, 150 deg from front |
| Fin tip distance from axis | 80.8 |

## Internal air volume

* **Body: 0.766 L**. That's the inner cavity minus the driver (57 x 30 mm), passive radiator (40 x 60 x 15 mm oval), battery, ballast cup, chassis, driver/radiator seats, spigots, and 31 cm3 of butyl pads.
* Nose cone interior: 0.032 L more, if the cone is left open to the body (total 0.798 L).
* For a sealed box, the knob shaft, LED and USB-C openings must be sealed.

## Assembly checks

* Driver (57 mm) goes in from the front through the 60.4 mm sound opening: OK
* Battery goes in through the 47.9 mm bottom opening (needs 41.6 mm): OK
* Top (nose cone) opening: 54.3 mm; bottom (collar) opening: 47.9 mm. Every internal part is sized to pass through one of them (the chassis is fitted as 4 pieces).
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
| body | pc_abs | 134.3 | 161.1 |
| nose_cone | aluminium | 12.6 | 34.0 |
| fin_1 | zinc_diecast | 17.8 | 117.7 |
| fin_2 | zinc_diecast | 17.8 | 117.7 |
| fin_3 | zinc_diecast | 17.8 | 117.7 |
| foot | zinc_diecast | 15.7 | 103.7 |
| grille | stainless_304 | 2.2 | 17.4 |
| bezel | aluminium | 3.1 | 8.4 |
| knob | brass | 1.0 | 8.7 |
| ballast | steel | 66.5 | 522.2 |
| chassis | steel | 13.2 | 103.7 |
| battery (bought-in) | - | - | 95.0 |
| driver (bought-in) | - | - | 65.0 |
| passive radiator (bought-in) | - | - | 40.0 |
| PCB (bought-in) | - | - | 30.0 |
| butyl damping pads | - | - | 50.0 |
| **Total** | | | **1592.5** |

* **Fins:** hollow die-cast with a 3 mm wall: **117.7 g each, 353.1 g for all 3** (solid would be 211.8 g each, 635.4 g).
* **Target: 1800 g. Total: 1592.5 g (-207.5 g).**
* **Ballast needed to hit the target: 729.8 g**; `BALLAST_MASS_G` is auto-sized to 522.2 g. The steel cup is 46.5 mm OD x 75.9 mm tall (top at 124.3 mm).

* **Centre of mass: 89.0 mm above the ground** (32% of overall height), offset 1.5 mm from the axis (towards the front grille and knob).
* Battery: 37 x 19 footprint, 65 tall, bottom at 48.4 mm, centre at 80.9 mm (the lowest position that fits and can be fitted through the 47.9 mm opening).

## Stability

* **Tips over at 22.4 deg of tilt** (worst direction, towards 0 deg, where 0 = front and 90 = right).
  * over the edge between fin tips 3 and 1 (towards 0 deg): 22.4 deg (CoM 36.6 mm inside that edge)
  * over the edge between fin tips 2 and 3 (towards 240 deg): 23.6 deg (CoM 38.8 mm inside that edge)
  * over the edge between fin tips 1 and 2 (towards 120 deg): 23.6 deg (CoM 38.8 mm inside that edge)
* How it's calculated: the rocket rests only on its three fin tips. Tilted about the line between two tips, it falls once the centre of mass passes over that line, so tip angle = atan(distance from CoM to the line / CoM height). For reference, the AV-equipment safety standard IEC 62368-1 tilts products by 10 deg in its stability test.
* The worst direction is towards the front, because the grille, bezel, knob and driver pull the CoM slightly forward, and a fin pair (not a single fin) faces that way.
* Mass low down: the 522 g steel ballast cup, the solid zinc foot and collar, and the battery all sit in the bottom third. The ballast adds mass, which makes the product feel solid and resist being nudged, but it only helps the tip angle as far as it lowers the CoM.

## Passive radiator

* **Fires down through the base** (the back stays smooth red). It's a round 44 mm radiator (35 mm radiating, 962 mm2) on the collar, which acts as its baffle.
* Exit path: a 37.0 mm hole in the collar, then a 9.2 mm gap between the collar (21.1 mm) and the foot stub (11.8 mm), which hangs on 3 posts behind the fins. Exit area 962 mm2 (1 x radiator area).
* That lifts the body from 18.2 mm to **27.4 mm off the ground**, and the red body is 7.6 mm shorter (overall height is fixed).
* **Mass target not met:** at most 522.2 g of steel ballast fits below the driver, leaving the total 207.5 g short. Use a denser ballast (tungsten alloy) or accept a lower target. `python compare_pr.py` compares the options.

## Assembly steps that need a professional to resolve

The model proves the parts fit. These steps still need a mechanical or manufacturing engineer to resolve before tooling:

1. **Tool access to the fin bolts.** The six M4 bolts go radially from inside the body through the wall into the fins, with their heads on the fin brackets about 40 mm from the axis, at 64.4 and 83.6 mm up. A straight driver would come in along the bolt axis, from the centre of the body, which is where the ballast cup and battery sit. The only ways in are the collar opening (about 48 mm, below) and the driver hole (60 mm, well above). The brackets also bolt to the ballast cup, so the order of assembly is circular. Options: fit the fins and brackets before the ballast/battery using an offset or right-angle driver; use captive studs cast into the fins with nuts inside; or bolt the brackets to the cup with vertical screws reachable from the collar opening.
2. **Moulding the body.** A one-piece shell whose belly (95 mm) is much wider than its end openings (about 48/54 mm) can't be injection-moulded on a simple core. It needs a collapsible core, or two halves welded together (the seam disappears under the lacquer), and the internal driver and radiator seats may have to become separate parts. This decision affects the split strategy and the fitting sequence.
3. **Blind assembly and wiring.** The battery, ballast and radiator go in through a ~48 mm opening, and the knob encoder's nut sits about 40 mm below the driver hole. Connectors, service loops and special tools need defining, along with a repair/disassembly sequence.
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
| fin_1.stl | zinc_diecast | lying on its side, tilted 7.7 deg so one tapered face is flat on the bed |
| fin_2.stl | zinc_diecast | lying on its side, tilted 7.7 deg so one tapered face is flat on the bed |
| fin_3.stl | zinc_diecast | lying on its side, tilted 7.7 deg so one tapered face is flat on the bed |
| foot.stl | zinc_diecast | upright, foot stub on the bed |
| grille.stl | stainless_304 | upright as fitted, standing on its lower edge |
| bezel.stl | aluminium | upright as fitted, standing on its lower edge |
| knob.stl | brass | front face down on the bed, shaft bore facing up |
| internal/ballast.stl | steel | internal production part (as assembled; printing is optional) |
| internal/chassis.stl | steel | internal production part (as assembled; printing is optional) |

