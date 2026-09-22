"""
Regenerate everything in ./output from params.py:

    python build.py              # full build: STEP, STLs, renders, report
    python build.py --no-render  # skip the PNGs (faster)
    python build.py --hex        # force the honeycomb grille on for this run
    python build.py --flat       # force the honeycomb off (plain disc grille)
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import shutil
import time
from pathlib import Path

from build123d import Color, Compound, Pos, Rot, export_step, export_stl

import analysis
import model as geometry
import params as p

OUT = Path(__file__).parent / "output"

def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


GOLD_RGB = _hex(p.GOLD_HEX)
RED_RGB = _hex(p.RED_HEX)


# How each part is turned for 3D printing: (orientation, supports needed).
# Listed in the report and in print_prototype/PRINT_NOTES.md.
def _print_pose(name, shape, info, internal=()):
    if name.startswith("body"):
        # upside down: the flat top rim sits on the bed and the walls lean
        # < 45 deg everywhere, so it prints without support
        s = Rot(180, 0, 0) * shape
        how = ("upside down, cone-joint rim on the bed",
               "No. Walls lean less than 30 deg; small holes bridge")
    elif name == "nose_cone":
        s = shape
        how = ("upright, spigot ring on the bed", "No")
    elif name.startswith("fin"):
        k = int(name.split("_")[1]) if name.split("_")[1].isdigit() else 1
        ang = p.FIN_ANGLE_OFFSET_DEG + (k - 1) * 360 / p.FIN_COUNT
        # back to its own plane, then tilt by the taper so one face lies flat
        s = Rot(90, 0, 0) * Rot(0, 0, -info["fin_taper_half_deg"]) * Rot(0, 0, 90 - ang) * shape
        how = (f"lying on its side, tilted {info['fin_taper_half_deg']:.1f} deg so one tapered face "
               "is flat on the bed", "No (use a brim for adhesion)")
    elif name == "foot" and info.get("pr_position") == "base":
        s = shape
        how = ("upright, foot stub on the bed",
               "Yes, under the collar ring (it overhangs the posts by about 9 mm)")
    elif name == "foot":
        s = Rot(180, 0, 0) * shape
        how = ("upside down, spigot on the bed", "No")
    elif name in ("grille", "bezel", "rear_grille", "rear_bezel"):
        # upright, as fitted: the part curves round the vertical axis, so its
        # walls print vertical and the pointy-top hexagons are self-supporting
        s = shape
        how = ("upright as fitted, standing on its lower edge",
               "Yes, build-plate-only supports under the lower third of the edge")
    elif name == "knob":
        s = Rot(90, 0, 0) * shape
        how = ("front face down on the bed, shaft bore facing up", "No")
    elif name in internal:
        s, how = shape, ("internal production part (as assembled; printing is optional)", "-")
    else:
        s, how = shape, ("as modelled", "check in slicer")
    bb = s.bounding_box()
    s = Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * s
    return s, how


def export_all(m):
    OUT.mkdir(exist_ok=True)
    stl_dir = OUT / "stl"
    if stl_dir.exists():
        shutil.rmtree(stl_dir)
    stl_dir.mkdir()

    # STEP: one assembly, each part named and coloured
    children = []
    for name, shape in m.parts.items():
        s = shape
        s.label = name
        s.color = Color(*(RED_RGB if name.startswith("body") else
                          (0.55, 0.56, 0.58) if name in m.internal else GOLD_RGB))
        children.append(s)
    assy = Compound(children=children, label="atelier_rocket_speaker")
    export_step(assy, str(OUT / "atelier_assembly.step"))

    poses = {}
    (stl_dir / "internal").mkdir()
    for name, shape in m.parts.items():
        s, how = _print_pose(name, shape, m.info, m.internal)
        sub = stl_dir / "internal" if name in m.internal else stl_dir
        export_stl(s, str(sub / f"{name}.stl"),
                   tolerance=p.STL_TOLERANCE, angular_tolerance=p.STL_ANGULAR_TOLERANCE)
        poses[name] = how[0]
    return poses


PRINT_MATERIAL = {
    "body": ("PLA+ or PETG", "0.12-0.16 mm layers; 3-4 walls; 15% infill. Sand, filler-prime, then "
             "automotive red and 2K clear coat for the lacquer look"),
    "nose_cone": ("PLA+", "0.12 mm layers for a smooth cone; gold paint or gold PLA"),
    "fin": ("PLA+ or PETG", "Solid in this version. 30-40% infill adds some weight. The 3.3 mm "
            "pilot holes take M4 self-tapping screws from inside, or glue with epoxy"),
    "foot": ("PLA+", "Friction-fits into the body (0.2 mm clearance); sand to fit"),
    "grille": ("Resin (SLA/MSLA) recommended", "The 2.2 mm honeycomb with 0.7 mm webs is at the limit of "
               "FDM (needs a 0.2 mm nozzle). Glue into the recess"),
    "bezel": ("Resin or PLA+", "Glue into the recess over the grille edge"),
    "knob": ("Resin or PLA+", "Press-fits on a 6 mm shaft; for a mock-up, glue a short 6 mm dowel"),
}


def export_print_prototype(m):
    """Visible parts only, fins solid, no internals, each turned for printing."""
    d = OUT / "print_prototype"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    rows, parts_for_mass = [], {}
    for name, shape in m.parts.items():
        if name in m.internal:
            continue
        if name.startswith("fin_"):
            if name != "fin_1":
                continue
            shape = m.info["fins_solid"][0]
            fname, qty = "fin_x3", p.FIN_COUNT
        else:
            fname, qty = name, 1
        s, (orient, supports) = _print_pose(name, shape, m.info)
        export_stl(s, str(d / f"{fname}.stl"),
                   tolerance=p.STL_TOLERANCE, angular_tolerance=p.STL_ANGULAR_TOLERANCE)
        bb = s.bounding_box()
        key = "fin" if name.startswith("fin") else name.replace("rear_", "")
        mat, notes = PRINT_MATERIAL.get(key, ("PLA+", ""))
        rows.append((fname, qty, mat, orient, supports, notes, bb.size))
    for name, shape in m.parts.items():
        if name not in m.internal:
            parts_for_mass[name] = (m.info["fins_solid"][int(name[4:]) - 1]
                                    if name.startswith("fin_") else shape)

    # mass and stability of the printed prototype (all PLA, no internals)
    from build123d import CenterOf
    import numpy as np
    tot, mom = 0.0, np.zeros(3)
    for shape in parts_for_mass.values():
        g = shape.volume / 1000 * p.MATERIAL_DENSITY["pla"] * 0.6   # ~60% of solid (walls + infill)
        c = shape.center(CenterOf.MASS)
        tot += g
        mom += g * np.array([c.X, c.Y, c.Z])
    com = mom / tot
    tip = analysis.tip_angles(m, com)[0]["angle"]
    biggest = max(rows, key=lambda r: r[6].Z * r[6].X * r[6].Y)

    L = []
    L.append("# ATELIER looks-like prototype: print notes")
    L.append("")
    L.append("Visible parts only: the fins are solid and there are no internals. The STLs are already "
             "turned to the print orientation below and sit on the bed at z = 0. Units are mm.")
    L.append("")
    L.append("| File | Qty | Material | Orientation | Supports? | Size X x Y x Z | Notes |")
    L.append("|---|---|---|---|---|---|---|")
    for fname, qty, mat, orient, sup, notes, sz in rows:
        L.append(f"| {fname}.stl | {qty} | {mat} | {orient} | {sup} | "
                 f"{sz.X:.0f} x {sz.Y:.0f} x {sz.Z:.0f} | {notes} |")
    L.append("")
    L.append("## General")
    L.append("")
    L.append(f"* **Printer size:** the largest part is {biggest[0]}.stl at {biggest[6].X:.0f} x "
             f"{biggest[6].Y:.0f} x {biggest[6].Z:.0f} mm, so you need at least {biggest[6].Z + 5:.0f} mm "
             "of build height (a Bambu X1/P1 or Prusa MK4/XL fits).")
    L.append("* Print a test fit of the cone and foot spigots first. Fit clearance is 0.2 mm per side, "
             "so PLA may need light sanding.")
    L.append("* Paint the body before fitting anything. The gold parts look best in metallic gold paint "
             "over a gloss black base, or in silk gold PLA.")
    L.append("* Honeycomb grilles: on FDM, set the slicer's 'detect thin walls' on, or print them in resin.")
    L.append(f"* **Weight and stability:** the printed prototype weighs about {tot:.0f} g (PLA at "
             f"~60% density), with its centre of mass at {com[2]:.0f} mm and a tip-over angle of about "
             f"{tip:.0f} deg. The production unit is {p.TARGET_MASS_G / 1000:.1f} kg. For a realistic "
             "feel, glue about 500 g of steel shot or fishing weights low inside the body.")
    L.append("")
    (d / "PRINT_NOTES.md").write_text("\n".join(L) + "\n")
    return d


def write_report(m, poses, build_seconds):
    I = m.info
    bb = analysis.overall_dims(m)
    air_body, air_cone = analysis.air_volume(m, p)
    rows, total_m, com = analysis.mass_properties(m, p)
    tips = analysis.tip_angles(m, com)
    worst = tips[0]

    def f(x, d=1):
        return f"{x:.{d}f}"

    lines = []
    L = lines.append
    L("# ATELIER rocket speaker: build report")
    L("")
    L(f"Generated {dt.datetime.now():%Y-%m-%d %H:%M} by `python build.py` in {build_seconds:.0f} s. "
      f"Split mode: **`{p.SPLIT_MODE}`**. Honeycomb grille: **{'on' if p.HEX_PATTERN_ENABLED else 'off (plain disc)'}**.")
    L("")
    L("## Overall dimensions")
    L("")
    L("| | mm |")
    L("|---|---|")
    L(f"| Overall height (ground to nose tip) | {f(bb.max.Z)} |")
    L(f"| Footprint across the fin tips (X x Y) | {f(bb.size.X)} x {f(bb.size.Y)} |")
    L(f"| Body max diameter | {f(2 * I['R'])} at {f(I['z_max'])} above ground |")
    L(f"| Body height (red) | {f(I['body_h'])} (from {f(I['z0'])} to {f(I['z_joint'])}) |")
    L(f"| Nose cone height | {f(I['cone_h'])} ({f(100 * p.CONE_HEIGHT_FRAC, 0)}% of the body) |")
    L(f"| Body diameter at the cone joint / at the collar | {f(2 * I['r_top'])} / {f(2 * I['r_bottom'])} |")
    L(f"| Grille diameter / bezel OD / sound opening | {f(I['grille_dia'])} / {f(I['bezel_od'])} / {f(I['sound_opening_dia'])} |")
    L(f"| Grille centre height | {f(I['z_grille'])} |")
    L(f"| Knob centre / LED height | {f(I['z_knob'])} / {f(I['z_led'])} |")
    L(f"| USB-C centre height, angle | {f(I['z_usbc'])}, {f(p.USBC_ANGLE_DEG, 0)} deg from front |")
    L(f"| Fin tip distance from axis | {f(I['fin_tip_reach'])} |")
    L("")
    L("## Internal air volume")
    L("")
    L(f"* **Body: {air_body:.3f} L**. That's the inner cavity minus the driver ({p.DRIVER_DIA:g} x "
      f"{p.DRIVER_DEPTH:g} mm), passive radiator ({p.PR_W:g} x {p.PR_H:g} x {p.PR_DEPTH:g} mm oval), "
      f"battery, ballast cup, chassis, driver/radiator seats, spigots, and "
      f"{p.BUTYL_MASS_G / p.BUTYL_DENSITY:.0f} cm3 of butyl pads.")
    L(f"* Nose cone interior: {air_cone:.3f} L more, if the cone is left open to the body "
      f"(total {air_body + air_cone:.3f} L).")
    L("* For a sealed box, the knob shaft, LED and USB-C openings must be sealed.")
    L("")
    L("## Assembly checks")
    L("")
    ok = lambda b: "OK" if b else "**PROBLEM**"
    L(f"* Driver ({p.DRIVER_DIA:g} mm) goes in from the front through the {f(I['sound_opening_dia'])} mm "
      f"sound opening: {ok(I['driver_through_opening'])}")
    if p.SPLIT_MODE == "nose_tail":
        L(f"* Battery goes in through the {f(2 * I['r_in_bottom'])} mm bottom opening "
          f"(needs {f(I['battery_min_opening'])} mm): {ok(2 * I['r_in_bottom'] >= I['battery_min_opening'])}")
    elif p.SPLIT_MODE == "nose":
        L(f"* Battery goes in through the {f(2 * I['r_in_top'])} mm top opening "
          f"(needs {f(I['battery_min_opening'])} mm): {ok(2 * I['r_in_top'] >= I['battery_min_opening'])}")
    L(f"* Top (nose cone) opening: {f(2 * I['r_in_top'])} mm; bottom (collar) opening: "
      f"{f(2 * I['r_in_bottom'])} mm. Every internal part is sized to pass through one of them "
      f"(the chassis is fitted as {I['chassis_pieces']} pieces).")
    L(f"* Fin brackets reach the ballast cup to bolt to it: {ok(I['bracket_reaches_cup'])}")
    for a, b, v in I["clashes"]:
        L(f"* {a.capitalize()} vs {b}: {ok(v < 1.0)}" + ("" if v < 1.0 else f" ({v / 1000:.1f} cm3 overlap)"))
    L("")
    L("## Mass and centre of mass (production materials)")
    L("")
    L("| Part | Material | Volume cm3 | Mass g |")
    L("|---|---|---|---|")
    for r in rows:
        v = "-" if r["volume_cm3"] is None else f(r["volume_cm3"])
        L(f"| {r['name']} | {r['material']} | {v} | {f(r['mass_g'])} |")
    L(f"| **Total** | | | **{f(total_m)}** |")
    L("")
    fin_rho = p.MATERIAL_DENSITY[p.PART_MATERIALS["fins"]]
    fin_solid = I["fin_solid_volume"] / 1000 * fin_rho
    fin_hollow = next(r["mass_g"] for r in rows if r["name"] == "fin_1")
    L(f"* **Fins:** hollow die-cast with a {p.FIN_WALL:g} mm wall: **{f(fin_hollow)} g each, "
      f"{f(fin_hollow * p.FIN_COUNT)} g for all {p.FIN_COUNT}** (solid would be {f(fin_solid)} g each, "
      f"{f(fin_solid * p.FIN_COUNT)} g).")
    ballast_now = next((r["mass_g"] for r in rows if r["name"] == "ballast"), 0.0)
    need = p.TARGET_MASS_G - (total_m - ballast_now)
    delta = total_m - p.TARGET_MASS_G
    L(f"* **Target: {f(p.TARGET_MASS_G, 0)} g. Total: {f(total_m)} g "
      f"({'+' if delta >= 0 else ''}{f(delta)} g).**")
    mode = "auto-sized" if p.BALLAST_MASS_G == "auto" else "set"
    L(f"* **Ballast needed to hit the target: {f(need)} g**; `BALLAST_MASS_G` is {mode} to "
      f"{f(I['ballast_mass'])} g. The steel cup is {f(I['ballast_dia'])} mm OD x "
      f"{f(I['ballast_h'])} mm tall (top at {f(I['ballast_top'])} mm).")
    L("")
    L(f"* **Centre of mass: {f(com[2])} mm above the ground** "
      f"({f(100 * com[2] / bb.max.Z, 0)}% of overall height), "
      f"offset {f(math.hypot(com[0], com[1]))} mm from the axis (towards the front grille and knob).")
    L(f"* Battery: {I['battery_orientation']}, bottom at {f(I['battery_z_bottom'])} mm, "
      f"centre at {f(I['battery_z_centre'])} mm (the lowest position that fits and can be "
      f"fitted through the {f(I['insert_opening_dia'])} mm opening).")
    L("")
    L("## Stability")
    L("")
    L(f"* **Tips over at {f(worst['angle'])} deg of tilt** (worst direction, towards "
      f"{f(worst['direction_deg'], 0)} deg, where 0 = front and 90 = right).")
    for t in tips:
        L(f"  * over the edge between fin tips {t['edge'][0] + 1} and {t['edge'][1] + 1} "
          f"(towards {f(t['direction_deg'], 0)} deg): {f(t['angle'])} deg "
          f"(CoM {f(t['dist'])} mm inside that edge)")
    L("* How it's calculated: the rocket rests only on its three fin tips. Tilted about the line "
      "between two tips, it falls once the centre of mass passes over that line, so "
      "tip angle = atan(distance from CoM to the line / CoM height). For reference, the "
      "AV-equipment safety standard IEC 62368-1 tilts products by 10 deg in its stability test.")
    L("* The worst direction is towards the front, because the grille, bezel, knob and driver pull the "
      "CoM slightly forward, and a fin pair (not a single fin) faces that way.")
    L(f"* Mass low down: the {f(I['ballast_mass'], 0)} g steel ballast cup, the solid zinc foot and "
      "collar, and the battery all sit in the bottom third. The ballast adds mass, which makes the "
      "product feel solid and resist being nudged, but it only helps the tip angle as far as it "
      "lowers the CoM.")
    L("")
    L("## Passive radiator")
    L("")
    if p.PR_POSITION == "base":
        L(f"* **Fires down through the base** (the back stays smooth red). It's a round {p.PR_BASE_DIA:g} mm "
          f"radiator ({p.PR_BASE_EFFECTIVE_DIA:g} mm radiating, {I['pr_sd']:.0f} mm2) on the collar, "
          f"which acts as its baffle.")
        L(f"* Exit path: a {f(I['pr_hole_dia'])} mm hole in the collar, then a {f(I['pr_plenum'])} mm "
          f"gap between the collar ({f(I['collar_bottom'])} mm) and the foot stub ({f(I['stub_top'])} mm), "
          f"which hangs on {p.FOOT_POSTS} posts behind the fins. Exit area {I['pr_exit_area']:.0f} mm2 "
          f"({p.PR_EXIT_AREA_RATIO:g} x radiator area).")
        L(f"* That lifts the body from {f(I['z0_ref'])} mm to **{f(I['z0'])} mm off the ground**, and the "
          f"red body is {f((p.OVERALL_HEIGHT - I['z0_ref']) / (1 + p.CONE_HEIGHT_FRAC) - I['body_h'])} mm "
          f"shorter (overall height is fixed).")
        if I["ballast_mass"] < need - 1:
            L(f"* **Mass target not met:** at most {f(I['ballast_max_g'])} g of "
              f"{p.PART_MATERIALS['ballast']} ballast fits below the driver, leaving the total "
              f"{f(p.TARGET_MASS_G - total_m)} g short. Use a denser ballast (tungsten alloy) or accept "
              f"a lower target. `python compare_pr.py` compares the options.")
    else:
        L(f"* On the rear: {p.PR_W:g} x {p.PR_H:g} mm oval behind a perforated gold cover "
          f"({I['rear_cover_size'][0]:.0f} x {I['rear_cover_size'][1]:.0f} mm) with a raised bezel, "
          f"matching the front grille.")
    L("")
    L("## Assembly steps that need a professional to resolve")
    L("")
    L("The model proves the parts fit. These steps still need a mechanical or manufacturing "
      "engineer to resolve before tooling:")
    L("")
    L("1. **Tool access to the fin bolts.** The six M4 bolts go radially from inside the body "
      "through the wall into the fins, with their heads on the fin brackets about 40 mm from the axis, "
      f"at {f(min(I['fin_bolt_z']))} and {f(max(I['fin_bolt_z']))} mm up. A straight driver would come in "
      "along the bolt axis, from the centre of the body, which is where the ballast cup and battery sit. The "
      "only ways in are the collar opening (about 48 mm, below) and the driver hole (60 mm, well above). "
      "The brackets also bolt to the ballast cup, so the order of assembly is circular. Options: fit the fins "
      "and brackets before the ballast/battery using an offset or right-angle driver; use captive studs "
      "cast into the fins with nuts inside; or bolt the brackets to the cup with vertical screws reachable "
      "from the collar opening.")
    L("2. **Moulding the body.** A one-piece shell whose belly (95 mm) is much wider than its end "
      "openings (about 48/54 mm) can't be injection-moulded on a simple core. It needs a collapsible core, "
      "or two halves welded together (the seam disappears under the lacquer), and the internal driver and "
      "radiator seats may have to become separate parts. This decision affects the split strategy and "
      "the fitting sequence.")
    L("3. **Blind assembly and wiring.** The battery, ballast and radiator go in through a ~48 mm opening, "
      "and the knob encoder's nut sits about 40 mm below the driver hole. Connectors, service loops and "
      "special tools need defining, along with a repair/disassembly sequence.")
    L("4. **Retaining the nose cone and the base module.** Both locate on slip-fit spigots only. They need "
      "a hidden fastening (bayonet, screws into the chassis, or adhesive). Also check what carries the load "
      "when the product is lifted by the body.")
    L("5. **Acoustics.** Sealed-box air-tightness (knob shaft, LED, USB-C, seams, grille seats) and "
      "passive radiator tuning." + (" The base radiator has about 26% less area than the rear oval, "
      "and its exit gap can be choked by soft surfaces such as a tablecloth, or collect dust. It needs "
      "measuring, not just calculating." if p.PR_POSITION == "base" else ""))
    L("6. **Matching the gold finish across materials.** Anodised aluminium (cone, bezels), plated zinc "
      "(fins, foot), PVD stainless (grilles) and brass (knob) all have to match one gold. That means "
      "colour-matching between suppliers, plus lacquer build-up at mating faces and a consistent 0.4 mm "
      "shadow line at the cone joint.")
    L("7. **Die-cast fins.** Draft angles, core design, gate position and porosity (which matters under plating), "
      "and a gasket or pad at the fin/body interface so fin loads don't crack the lacquer.")
    L("8. **Safety and certification.** Heat from the battery and amplifier in a sealed, steel-lined "
      "enclosure, UN38.3 for the battery, and IEC 62368-1 (including the stability test).")
    L("")
    L("## Parts and print orientation (output/stl)")
    L("")
    L("| STL | Production material | Print orientation |")
    L("|---|---|---|")
    for name, why in poses.items():
        path = f"internal/{name}.stl" if name in m.internal else f"{name}.stl"
        L(f"| {path} | {p.PART_MATERIALS[m.part_material_key[name]]} | {why} |")
    L("")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    return dict(air=air_body, com=com, total=total_m, tip=worst["angle"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-render", action="store_true", help="skip the PNG renders")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--hex", action="store_true", help="honeycomb grille on for this run")
    g.add_argument("--flat", action="store_true", help="honeycomb grille off for this run")
    args = ap.parse_args()
    if args.hex:
        p.HEX_PATTERN_ENABLED = True
    if args.flat:
        p.HEX_PATTERN_ENABLED = False

    t0 = time.time()
    print(f"Building model (split={p.SPLIT_MODE}, hex={p.HEX_PATTERN_ENABLED})...")
    m = geometry.build(p)
    print(f"  {len(m.parts)} parts in {time.time() - t0:.1f} s")
    print("Exporting STEP and STLs...")
    poses = export_all(m)
    print("Exporting the 3D-print prototype set...")
    export_print_prototype(m)
    if not args.no_render:
        print("Rendering previews...")
        import render
        render.render_views(m, p, OUT / "renders")
    print("Writing report...")
    s = write_report(m, poses, time.time() - t0)
    print(f"Done in {time.time() - t0:.0f} s -> {OUT}")
    print(f"  air volume {s['air']:.3f} L | mass {s['total']:.0f} g | "
          f"CoM {s['com'][2]:.1f} mm | tips at {s['tip']:.1f} deg")


if __name__ == "__main__":
    main()
