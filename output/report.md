# ATELIER rocket speaker: build report

Generated 2026-09-23 14:18 by `python build.py` in 194 s. Split mode: **`nose_tail`**. Honeycomb grille: **on**.

## Overall dimensions

| | mm |
|---|---|
| Overall height (ground to nose tip) | 280.0 |
| Footprint across the fin tips (X x Y) | 138.5 x 131.4 |
| Body max diameter | 96.8 at 123.8 above ground |
| Body height (red) | 209.1 (from 25.8 to 234.8) |
| Nose cone height | 45.2 (22% of the body) |
| Body diameter at the cone joint / at the collar | 53.6 / 50.3 |
| Grille diameter / bezel OD / sound opening | 74.0 / 80.0 / 61.2 |
| Grille centre height | 162.1 |
| Knob centre / LED height | 97.4 / 114.3 |
| USB-C port (in the collar cup) | face centre 16.3 mm up, 120 deg from front, facing 45 deg down |
| Collar cup / foot height | 13.8 / 10.0 (2 mm ground gap) |
| Fin tip distance from axis | 79.0 |

## Internal air volume

* **Body: 0.749 L**. That's the inner cavity minus the driver (57 x 30 mm), battery, ballast cup, chassis, driver seat, spigots, and 31 cm3 of butyl pads.
* Nose cone interior: 0.031 L more, if the cone is left open to the body (total 0.780 L).
* It's a **sealed box**: the knob shaft, LED light pipe, USB-C receptacle, grille seat and the cone and collar joints must all be airtight (see below).

## Assembly checks

* Driver (57 mm) goes in from the front through the 61.2 mm sound opening: OK
* Battery goes in through the 49.0 mm top (cone) opening (needs 41.6 mm): OK
* Top (nose cone) opening: 49.0 mm; bottom (collar) opening: 44.3 mm. Every internal part is sized to pass through one of them (the chassis is fitted as 4 pieces).
* Fin brackets reach the ballast cup to bolt to it: OK
* Driver vs battery: OK
* Driver vs chassis: OK
* Driver vs ballast: OK
* Battery vs chassis: OK
* Battery vs ballast: OK
* Chassis vs ballast: OK

## Mass and centre of mass (production materials)

| Part | Material | Volume cm3 | Mass g |
|---|---|---|---|
| body | pc_abs | 132.2 | 158.6 |
| nose_cone | aluminium | 12.1 | 32.8 |
| fin_1 | zinc_diecast | 16.6 | 109.7 |
| fin_2 | zinc_diecast | 16.6 | 109.7 |
| fin_3 | zinc_diecast | 16.6 | 109.7 |
| grille | stainless_304 | 2.5 | 19.8 |
| bezel | aluminium | 2.0 | 5.4 |
| grille_backing | acoustic_cloth | 1.6 | 0.8 |
| knob | brass | 1.1 | 9.0 |
| collar | zinc_diecast | 26.7 | 176.3 |
| foot | zinc_diecast | 2.3 | 15.4 |
| ballast | steel | 92.5 | 726.3 |
| chassis | steel | 10.7 | 84.1 |
| battery (bought-in) | - | - | 95.0 |
| driver (bought-in) | - | - | 65.0 |
| PCB (bought-in) | - | - | 30.0 |
| USB-C receptacle, sealed (bought-in) | - | - | 3.0 |
| butyl damping pads | - | - | 50.0 |
| **Total** | | | **1800.6** |

* **Fins:** hollow die-cast with a 3 mm wall: **109.7 g each, 329.2 g for all 3** (solid would be 129.6 g each, 388.7 g).
* **Target: 1800 g. Total: 1800.6 g (+0.6 g).**
* **Ballast needed to hit the target: 725.7 g**; `BALLAST_MASS_G` is auto-sized to 726.3 g. The steel cup is 47.6 mm OD x 98.3 mm tall (top at 130.0 mm).

* **Centre of mass: 82.7 mm above the ground** (30% of overall height), offset 1.3 mm from the axis (towards the front grille and knob).
* Battery: 37 x 19 footprint, 65 tall, bottom at 31.8 mm, centre at 64.3 mm (the lowest position that fits and can be fitted through the 49.0 mm opening).

## Stability

* **Tips over at 23.3 deg of tilt** (worst direction, towards 0 deg, where 0 = front and 90 = right).
  * over the edge between fin tips 3 and 1 (towards 0 deg): 23.3 deg (CoM 35.6 mm inside that edge)
  * over the edge between fin tips 2 and 3 (towards 240 deg): 24.3 deg (CoM 37.4 mm inside that edge)
  * over the edge between fin tips 1 and 2 (towards 120 deg): 24.5 deg (CoM 37.6 mm inside that edge)
* How it's calculated: the rocket rests only on its three fin tips. Tilted about the line between two tips, it falls once the centre of mass passes over that line, so tip angle = atan(distance from CoM to the line / CoM height). For reference, the AV-equipment safety standard IEC 62368-1 tilts products by 10 deg in its stability test.
* The worst direction is towards the front, because the grille, bezel, knob and driver pull the CoM slightly forward, and a fin pair (not a single fin) faces that way.
* Mass low down: the 726 g steel ballast cup, the solid zinc foot and collar, and the battery all sit in the bottom third. The ballast adds mass, which makes the product feel solid and resist being nudged, but it only helps the tip angle as far as it lowers the CoM.

## Sealed enclosure

* **No passive radiator** (`PR_POSITION = "none"`): the body is a sealed box of 0.749 L. The gold collar cup is a solid zinc plug that closes the bottom of the body and sits straight on the foot, with no vent or shadow gap.
* Every opening has to be airtight: the knob shaft (sealed encoder or O-ring), the LED light pipe, the USB-C receptacle (below), the grille seat, and the cone and collar spigots (an O-ring or gasket on each).
* `PR_POSITION = "base"` or `"rear"` still builds the radiator layouts for comparison (`python compare_pr.py`). Those use a USB-C port in the body instead.

## USB-C port

* **In the gold collar cup**, at 120 deg (midway between the side fin at 60 deg and the rear fin at 180 deg), facing 45 deg down. It's out of sight from normal viewing heights, and the cable drops between those two fins.
* The port face is sunk 1.5 mm into the cup, with its centre 16.3 mm off the ground. That leaves at least 1 mm of zinc round the receptacle pocket, and a flat seat for the plug.
* **Sealed receptacle:** because the enclosure is sealed, it has to be an IP67-type mid-mount receptacle with its own gasket (10.6 x 4.9 mm envelope modelled). The pocket behind it opens into the battery bay, so any leak there is a leak in the box.
* **Wiring:** a 4 mm channel (11.4 mm long) runs from the back of the pocket through the collar spigot into the battery bay. A 5 x 4 mm slot then runs up the ballast cup beside the battery to the top of the cup, where the battery and USB wires join the harness to the PCB on the spine (about 16 cm in total).

**Ships with a right-angle USB-C cable.** It should be a **side-angled** (left/right) type. A USB-C plug goes in either way up, so the cable has to fit in both orientations:

| Plug | Clearance to fins | to foot knob | above ground | to red body | Fits? |
|---|---|---|---|---|---|
| Straight plug (checked for any third-party cable), overmold 12.35 x 6.5 x 16 mm | 15.8 | 6.1 | 2.7 | - | Yes |
| Right-angle, cable leaving up | 15.8 | 6.1 | 6.2 | 5.3 | Yes |
| Right-angle, cable leaving down | 15.8 | 1.5 | -5.6 | 7.2 | **No** |
| Right-angle, cable leaving side A (towards the rear fin) | 10.1 | 6.1 | 6.2 | 7.2 | Yes |
| Right-angle, cable leaving side B (towards the side fin) | 10.1 | 6.1 | 6.2 | 7.2 | Yes |

* A side-angled plug fits both ways up. An up/down-angled plug only fits one way: flipped over, its boot points into the ground. So the shipped cable should be side-angled, and the quick-start guide should still say which way the cable runs.
* With a straight cable the plug's rigid part ends just above the ground, so the cable has to bend tighter than ideal right at its strain relief. That's another reason to ship the right-angle cable.


## Assembly steps that need a professional to resolve

The model proves the parts fit. These steps still need a mechanical or manufacturing engineer to resolve before tooling:

1. **Tool access to the fin bolts.** The six M4 bolts go radially from inside the body through the wall into the fins, with their heads on the fin brackets about 40 mm from the axis, at 58.2 and 65.9 mm up. A straight driver would come in along the bolt axis, from the centre of the body, which is where the ballast cup and battery sit. The only ways in are the end openings (44.3 mm at the bottom, 49.0 mm at the cone) and the driver hole (61.2 mm, well above). The brackets also bolt to the ballast cup, so the order of assembly is circular. Options: fit the fins and brackets before the ballast/battery using an offset or right-angle driver; use captive studs cast into the fins with nuts inside; or bolt the brackets to the cup with vertical screws reachable from the collar opening.
2. **Moulding the body.** A one-piece shell whose belly (95 mm) is much wider than its end openings can't be injection-moulded on a simple core. It needs a collapsible core, or two halves welded together (the seam disappears under the lacquer), and the internal driver seat may have to become a separate part. This decision affects the split strategy and the fitting sequence.
3. **Blind assembly and wiring.** The battery and ballast go in through a ~49 mm opening, and the knob encoder's nut sits about 40 mm below the driver hole. The USB-C wires have to be fed up the ballast slot before the collar is fitted, so they need a connector at the top of the cup. Connectors, service loops and special tools need defining, along with a repair/disassembly sequence.
4. **Retaining the nose cone and the base module.** Both locate on slip-fit spigots only. They need a hidden fastening (bayonet, screws into the chassis, or adhesive). Also check what carries the load when the product is lifted by the body.
5. **Acoustics.** Sealed-box air-tightness (knob shaft, LED, USB-C, seams, grille seats) and tuning the driver to the sealed volume (a sealed box of this size limits the bass extension, so the DSP EQ has to make up the difference within the driver's excursion).
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
| grille_backing.stl | acoustic_cloth | upright as fitted (or cut from cloth) |
| knob.stl | brass | front face down on the bed, shaft bore facing up |
| collar.stl | zinc_diecast | upside down, spigot on the bed |
| foot.stl | zinc_diecast | upside down, flat top on the bed |
| internal/ballast.stl | steel | internal production part (as assembled; printing is optional) |
| internal/chassis.stl | steel | internal production part (as assembled; printing is optional) |

