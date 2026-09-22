"""
Compare passive-radiator layouts side by side:

    python compare_pr.py

Builds the model twice, once with the radiator firing down through the base
(smooth red back) and once on the rear behind a perforated gold cover, using
the current params.py for everything else. It also works out the numbers for a
tungsten-alloy ballast in the base layout. Writes renders and a table to
output/pr_comparison/.
"""
from __future__ import annotations

import copy
import time
from pathlib import Path

import analysis
import model as geometry
import params as p
import render

OUT = Path(__file__).parent / "output" / "pr_comparison"


def evaluate(label, pr_position, ballast_material=None, do_render=True):
    saved = (p.PR_POSITION, copy.deepcopy(p.PART_MATERIALS))
    p.PR_POSITION = pr_position
    if ballast_material:
        p.PART_MATERIALS["ballast"] = ballast_material
    try:
        t0 = time.time()
        m = geometry.build(p)
        rows, total, com = analysis.mass_properties(m, p)
        tip = analysis.tip_angles(m, com)[0]["angle"]
        air, _ = analysis.air_volume(m, p)
        I = m.info
        res = dict(label=label, z0=I["z0"], body_h=I["body_h"], air=air, mass=total,
                   ballast=I["ballast_mass"], ballast_mat=p.PART_MATERIALS["ballast"],
                   com=com[2], tip=tip, batt_c=I["battery_z_centre"],
                   clashes=[c for c in I["clashes"] if c[2] > 1.0], info=I)
        if do_render:
            OUT.mkdir(parents=True, exist_ok=True)
            files = render.render_views(m, p, OUT, views=["rear", "three_quarter_rear"],
                                        prefix=label, section=False)
            files = [f for f in files if "overview" not in f.name and "front_side" not in f.name]
            if pr_position == "base":
                files.append(render.render_underside(m, p, OUT / f"{label}_underside.png"))
            res["sheet"] = render.contact_sheet(files, OUT / f"{label}_sheet.png")
        print(f"  {label}: built and measured in {time.time() - t0:.0f} s")
        return res
    finally:
        p.PR_POSITION, p.PART_MATERIALS = saved[0], saved[1]


def main():
    print("Comparing passive radiator layouts...")
    results = [
        evaluate("base_steel", "base"),
        evaluate("rear_cover", "rear"),
        evaluate("base_tungsten", "base", "tungsten_alloy", do_render=False),
    ]
    r0 = results[1]
    lines = ["# Passive radiator: down through the base vs rear cover", "",
             f"Target mass {p.TARGET_MASS_G:.0f} g. Ballast is auto-sized to the target but can't "
             f"rise into the driver. Everything else is as in params.py.", "",
             "| | " + " | ".join(r["label"] for r in results) + " |",
             "|---|" + "---|" * len(results)]

    def row(name, fmt, key):
        lines.append(f"| {name} | " + " | ".join(fmt.format(r[key]) for r in results) + " |")

    row("Body underside above ground (mm)", "{:.1f}", "z0")
    row("Red body height (mm)", "{:.1f}", "body_h")
    row("Internal air volume (L)", "{:.3f}", "air")
    row("Total mass (g)", "{:.0f}", "mass")
    row("Ballast mass (g)", "{:.0f}", "ballast")
    row("Ballast material", "{}", "ballast_mat")
    row("Battery centre height (mm)", "{:.1f}", "batt_c")
    row("Centre of mass height (mm)", "{:.1f}", "com")
    row("Tip-over angle (deg)", "{:.1f}", "tip")
    lines.append("| Internal clashes | " + " | ".join(
        "none" if not r["clashes"] else ", ".join(f"{a}/{b}" for a, b, _ in r["clashes"])
        for r in results) + " |")
    ib = results[0]["info"]
    lines += ["",
              "## Base-firing radiator details", "",
              f"* Round radiator, {p.PR_BASE_DIA:g} mm frame / {p.PR_BASE_EFFECTIVE_DIA:g} mm radiating: "
              f"area {ib['pr_sd']:.0f} mm2, against about "
              f"{3.1416 / 4 * (p.PR_W - 2 * p.PR_FLANGE) * (p.PR_H - 2 * p.PR_FLANGE):.0f} mm2 for the "
              f"{p.PR_W:g} x {p.PR_H:g} rear oval. It has to pass the collar opening.",
              f"* Sound exits through a {ib['pr_hole_dia']:.0f} mm hole in the collar, then out through a "
              f"{ib['pr_plenum']:.1f} mm tall honeycomb mesh ring ({ib['mesh_holes']} holes, open area "
              f"{ib['pr_exit_area']:.0f} mm2 = {ib['pr_exit_area'] / ib['pr_sd']:.2f} x radiator area). "
              "The ring carries the stepped gold nozzle.",
              f"* The ring and nozzle lift the body from {ib['z0_ref']:.1f} to {ib['z0']:.1f} mm off the ground "
              f"(overall height fixed, so the red body gets {results[1]['body_h'] - results[0]['body_h']:.1f} mm shorter).",
              f"* With steel, the most ballast that fits below the driver is {ib['ballast_max_g']:.0f} g, so "
              f"the total is {p.TARGET_MASS_G - results[0]['mass']:.0f} g short of the target. Tungsten "
              f"alloy reaches it in a shorter cup.",
              ""]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "comparison.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
