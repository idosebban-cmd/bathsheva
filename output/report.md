# ATELIER rocket speaker: build report

Generated 2026-09-22 23:12 by `python build.py` in 115 s. Split mode: **`nose_tail`**. Honeycomb grille: **on**.

## Overall dimensions

| | mm |
|---|---|
| Overall height (ground to nose tip) | 280.0 |
| Footprint across the fin tips (X x Y) | 141.2 x 131.6 |
| Body max diameter | 95.0 at 124.3 above ground |
| Body height (red) | 202.2 (from 33.4 to 235.5) |
| Nose cone height | 44.5 (22% of the body) |
| Body diameter at the cone joint / at the collar | 58.9 / 52.3 |
| Grille diameter / bezel OD / sound opening | 65.4 / 73.4 / 60.4 |
| Grille centre height | 158.7 |
| Knob centre / LED height | 95.8 / 113.4 |
| USB-C centre height, angle | 61.7, 150 deg from front |
| Fin tip distance from axis | 80.8 |

## Internal air volume

* **Body: 0.745 L**. That's the inner cavity minus the driver (57 x 30 mm), passive radiator (40 x 60 x 15 mm oval), battery, ballast cup, chassis, driver/radiator seats, spigots, and 31 cm3 of butyl pads.
* Nose cone interior: 0.031 L more, if the cone is left open to the body (total 0.775 L).
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
| body | pc_abs | 131.2 | 157.4 |
| nose_cone | aluminium | 12.4 | 33.5 |
| fin_1 | zinc_diecast | 18.2 | 119.8 |
| fin_2 | zinc_diecast | 18.2 | 119.8 |
| fin_3 | zinc_diecast | 18.2 | 119.8 |
| grille | stainless_304 | 2.2 | 17.4 |
| bezel | aluminium | 3.1 | 8.5 |
| knob | brass | 1.0 | 8.6 |
| nozzle | zinc_diecast | 9.9 | 65.4 |
| base_mesh | stainless_304 | 1.7 | 13.8 |
| collar | zinc_diecast | 6.8 | 45.0 |
| ballast | steel | 64.0 | 502.5 |
| chassis | steel | 13.0 | 102.2 |
| battery (bought-in) | - | - | 95.0 |
| driver (bought-in) | - | - | 65.0 |
| passive radiator (bought-in) | - | - | 40.0 |
| PCB (bought-in) | - | - | 30.0 |
| butyl damping pads | - | - | 50.0 |
| **Total** | | | **1593.7** |

* **Fins:** hollow die-cast with a 3 mm wall: **119.8 g each, 359.4 g for all 3** (solid would be 215.4 g each, 646.3 g).
* **Target: 1800 g. Total: 1593.7 g (-206.3 g).**
* **Ballast needed to hit the target: 708.9 g**; `BALLAST_MASS_G` is auto-sized to 502.5 g. The steel cup is 46.5 mm OD x 72.8 mm tall (top at 127.2 mm).

* **Centre of mass: 91.5 mm above the ground** (33% of overall height), offset 1.5 mm from the axis (towards the front grille and knob).
* Battery: 37 x 19 footprint, 65 tall, bottom at 54.4 mm, centre at 86.9 mm (the lowest position that fits and can be fitted through the 47.9 mm opening).

## Stability

* **Tips over at 21.8 deg of tilt** (worst direction, towards 0 deg, where 0 = front and 90 = right).
  * over the edge between fin tips 3 and 1 (towards 0 deg): 21.8 deg (CoM 36.6 mm inside that edge)
  * over the edge between fin tips 2 and 3 (towards 240 deg): 23.0 deg (CoM 38.9 mm inside that edge)
  * over the edge between fin tips 1 and 2 (towards 120 deg): 23.0 deg (CoM 38.9 mm inside that edge)
* How it's calculated: the rocket rests only on its three fin tips. Tilted about the line between two tips, it falls once the centre of mass passes over that line, so tip angle = atan(distance from CoM to the line / CoM height). For reference, the AV-equipment safety standard IEC 62368-1 tilts products by 10 deg in its stability test.
* The worst direction is towards the front, because the grille, bezel, knob and driver pull the CoM slightly forward, and a fin pair (not a single fin) faces that way.
* Mass low down: the 503 g steel ballast cup, the solid zinc foot and collar, and the battery all sit in the bottom third. The ballast adds mass, which makes the product feel solid and resist being nudged, but it only helps the tip angle as far as it lowers the CoM.

## Passive radiator

* **Fires down through the base** (the back stays smooth red). It's a round 44 mm radiator (35 mm radiating, 962 mm2) on the collar, which acts as its baffle.
* Exit path: a 37.0 mm hole in the collar, then out through a 45.0 mm diameter, 17.0 mm tall ring of the grille's honeycomb sheet (5 rows, 235 holes). Its open area is 985 mm2 (1.02 x radiator area). The ring hides the inside and carries the stepped gold nozzle below it (throat 18.3 mm, exit 33.2 mm, 2 mm off the ground); there are no posts.
* That lifts the body from 18.2 mm to **33.4 mm off the ground**, and the red body is 12.4 mm shorter (overall height is fixed).
* **Mass target not met:** at most 502.5 g of steel ballast fits below the driver, leaving the total 206.3 g short. Use a denser ballast (tungsten alloy) or accept a lower target. `python compare_pr.py` compares the options.

## Assembly steps that need a professional to resolve

The model proves the parts fit. These steps still need a mechanical or manufacturing engineer to resolve before tooling:

1. **Tool access to the fin bolts.** The six M4 bolts go radially from inside the body through the wall into the fins, with their heads on the fin brackets about 40 mm from the axis, at 69.4 and 88.2 mm up. A straight driver would come in along the bolt axis, from the centre of the body, which is where the ballast cup and battery sit. The only ways in are the collar opening (about 48 mm, below) and the driver hole (60 mm, well above). The brackets also bolt to the ballast cup, so the order of assembly is circular. Options: fit the fins and brackets before the ballast/battery using an offset or right-angle driver; use captive studs cast into the fins with nuts inside; or bolt the brackets to the cup with vertical screws reachable from the collar opening.
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
| grille.stl | stainless_304 | upright as fitted, standing on its lower edge |
| bezel.stl | aluminium | upright as fitted, standing on its lower edge |
| knob.stl | brass | front face down on the bed, shaft bore facing up |
| nozzle.stl | zinc_diecast | upright, exit rim on the bed (deflector cone on top) |
| base_mesh.stl | stainless_304 | upright as fitted (a ring standing on its lower edge) |
| collar.stl | zinc_diecast | upside down, spigot on the bed |
| internal/ballast.stl | steel | internal production part (as assembled; printing is optional) |
| internal/chassis.stl | steel | internal production part (as assembled; printing is optional) |

