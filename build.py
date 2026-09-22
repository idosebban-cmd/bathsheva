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


# How each part is turned for 3D printing, and why (listed in the report too).
def _print_pose(name, shape, internal=()):
    if name.startswith("body"):
        # upside down: the flat top rim sits on the bed and the walls lean
        # < 45 deg almost everywhere, so it prints without support
        s = Rot(180, 0, 0) * shape
        why = "upside down, top rim on the bed (walls self-supporting)"
    elif name == "nose_cone":
        s = shape
        why = "upright, spigot ring on the bed"
    elif name.startswith("fin"):
        ang = p.FIN_ANGLE_OFFSET_DEG + (int(name.split("_")[1]) - 1) * 360 / p.FIN_COUNT
        s = Rot(90, 0, 0) * Rot(0, 0, 90 - ang) * shape
        why = "lying flat on its side (tapered faces need light support or a brim)"
    elif name == "foot":
        s = Rot(180, 0, 0) * shape
        why = "upside down, spigot on the bed"
    elif name in ("grille", "bezel"):
        s = Rot(-90, 0, 0) * shape
        why = "front face up (curved, like a shallow dome)"
    elif name == "knob":
        s = Rot(90, 0, 0) * shape
        why = "front face down on the bed, shaft bore facing up"
    elif name in internal:
        s, why = shape, "internal production part (as assembled; printing is optional)"
    else:
        s, why = shape, "as modelled"
    bb = s.bounding_box()
    s = Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * s
    return s, why


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
        s, why = _print_pose(name, shape, m.internal)
        sub = stl_dir / "internal" if name in m.internal else stl_dir
        export_stl(s, str(sub / f"{name}.stl"),
                   tolerance=p.STL_TOLERANCE, angular_tolerance=p.STL_ANGULAR_TOLERANCE)
        poses[name] = why
    return poses


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
    L(f"* **Ballast needed to hit the target: {f(need)} g**; `BALLAST_MASS_G` is set to "
      f"{f(p.BALLAST_MASS_G)} g. The steel cup is {f(I['ballast_dia'])} mm OD x "
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
    L(f"* Mass low down: the {f(p.BALLAST_MASS_G, 0)} g steel ballast cup, the solid zinc foot and "
      "collar, and the battery all sit in the bottom third. The ballast adds mass, which makes the "
      "product feel solid and resist being nudged, but it only helps the tip angle as far as it "
      "lowers the CoM.")
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
