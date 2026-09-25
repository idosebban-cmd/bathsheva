"""
Build Faro.

    python faro/build.py --draft    # front + side + underside renders -> faro/output/draft/
    python faro/build.py            # final: STEP, STLs, renders, print set + PRINT_NOTES.md
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from build123d import Color, Compound, Pos, Rot, export_step, export_stl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lamp  # noqa: E402
import params as p  # noqa: E402
import studio  # noqa: E402

OUT = HERE / "output"


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


COLOURS = {"base": p.WALNUT_HEX, "band_cream": p.CREAM_HEX, "tower": p.CREAM_HEX, "band_red": p.RED_HEX,
           "cap": p.RED_HEX, "felt_pad": "#2F2D2B", "base_plate": "#4A4541", "lantern_glass": p.GLOW_HEX}

# How each printed part is made. name: (qty, material, orientation, supports, notes, turn-to-print)
# The turn takes the part from its assembled position to its print position.
FLIP = lambda s: Rot(180, 0, 0) * s
FACE_UP = lambda s: Rot(-90, 0, 0) * s         # front (-Y) face up
FACE_DOWN = lambda s: Rot(90, 0, 0) * s        # front (-Y) face on the bed
SCREWED = p.BASE_FIXING == "screwed"
PRINT = {
    "base": (1, "PLA+ (wood-fill PLA, or paint walnut)", "upright, open underside on the bed",
             "Yes: tree supports inside the hollow base only (hidden), under its ceiling"
             + (" and bosses" if SCREWED else ""),
             (f"Production: CNC-turned walnut with {p.SCREW_SIZE} threaded inserts in the bosses. Melt "
              f"{p.SCREW_SIZE} heat-set inserts into the bosses" if SCREWED else
              "Sponged burnt umber for the walnut effect. The fairy lights come in through the rear port"), None),
    "base_plate": (1, "PLA+ or PETG, black", "felt recess up (flat top face on the bed)", "No",
                   ("Glue the 4 magnets into their pockets, flush with the recess floor" if SCREWED else
                    "A plain plate: glue it into the rebate under the base; the felt sticks into its shallow "
                    "recess"), FLIP),
    "nameplate": (1, "Resin, or PLA+ painted brass", "outer face (lettering) up", "Yes: supports under the curved back (the plate arches about 3 mm)",
                  "Glue into the recess on the base front. Production: etched or engraved brass", FACE_UP),
    "band_cream": (1, "PLA+ or PETG", "upright", "No", "Paint cream lacquer; glue onto the base top", None),
    "band_red": (1, "PLA+ or PETG", "upright, wide end down", "No", "Paint red lacquer", None),
    "tower": (1, "PLA+ or PETG", "upright, wide end down", "No: the window arches are self-supporting",
              "Paint cream lacquer (mask the window edges)", None),
    "window_diffuser": (1, "Translucent resin, sanded", "outer face up", "Yes, on the inner face only",
                        "One per window, numbered from the lowest (front) up; each follows the tower's "
                        "taper at its own height, so keep them in order. Or cut from 1 mm opal "
                        "polycarbonate. Glue behind its window", None),
    "knob": (1, "Resin or PLA+", "front face down", "No", "Brass paint; glue on, or fit on a 6 mm shaft", FACE_DOWN),
    "gallery": (1, "Resin recommended (PLA+ with a 0.2 mm nozzle)", "upright, platform on the bed",
                "No: posts are vertical; the rails bridge about 17 mm between posts",
                "1.6 mm posts and rails. Brass paint or brass-fill filament", None),
    "lantern_frame": (1, "Resin recommended", "upright, bottom ring on the bed",
                      "No: the bayonet lip overhangs only 1.8 mm", "Check the cap twists on before painting", None),
    "lantern_glass": (1, "Translucent PETG or clear resin, sanded/frosted", "upright", "No",
                      "Stands on the gallery platform; the frame is lowered over it", None),
    "cap": (1, "PLA+ or resin", "upright, spigot on the bed",
            "Yes: under the rim (build-plate only); the lugs need none",
            "Paint red lacquer. Twist on: drop the lugs through the slots, turn clockwise to the stop", None),
    "finial": (1, "Resin, or PLA+ painted brass", "upright, neck on the bed", "Yes, light supports under the ball",
               "Glue into the cap's collar", None),
}
NOT_PRINTED = [
    ("felt_pad", ("Cut from 1.5 mm felt laminated to a 0.4 mm steel disc (self-adhesive felt on steel "
                  "shim works). The STL is only a size reference") if SCREWED else
     "Cut from black self-adhesive felt, trimmed to size, and stuck on. The STL is only a size reference"),
]
if SCREWED:
    RENDER_ONLY = [
        ("Battery", f"{p.BATTERY_SIZE[0]:g} x {p.BATTERY_SIZE[1]:g} x {p.BATTERY_SIZE[2]:g} mm 2 x 18650 pack "
         "(placeholder)"),
        ("LED module", f"Ø{p.LED_DIA:g} x {p.LED_H:g} mm (placeholder)"),
        ("USB-C receptacle", "board-mounted, behind the rear port (placeholder)"),
        ("Screws", f"{p.SCREWS} x {p.SCREW_SIZE} x 8 countersunk, hex socket"),
        ("Threaded inserts", f"{p.SCREWS} x {p.SCREW_SIZE} heat-set inserts for the base bosses"),
        ("Magnets", f"{p.MAGNETS} x Ø{p.MAGNET_DIA:g} x {p.MAGNET_THICK:g} mm N52 discs"),
    ]
else:   # the looks-like prototype, as in the build manual
    RENDER_ONLY = [
        ("Fairy lights", "Warm white copper fairy lights with a 3 x AA battery box (the box stays outside, "
         "behind the lamp)"),
        ("LED puck", f"Rechargeable warm white LED puck, under {p.LED_PUCK_MAX_DIA:g} mm across, for the "
         "brightness test (it rests on the ledge inside the gallery)"),
        ("Coins", "A few coins, taped low inside the base, for weight"),
        ("Epoxy", "Araldite Rapid, with cocktail sticks"),
    ]


def _print_pose(name, shape):
    key = "window_diffuser" if name.startswith("window_diffuser") else name
    qty, mat, orient, sup, notes, turn = PRINT[key]
    s = turn(shape) if turn else shape
    bb = s.bounding_box()
    s = Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * s
    return s, (qty, mat, orient, sup, notes)


def final(m):
    OUT.mkdir(exist_ok=True)
    # STEP assembly
    kids = []
    for name, shape in m.parts.items():
        s = shape
        s.label = name
        s.color = Color(*_hex(COLOURS.get(name, p.BRASS_HEX)))
        kids.append(s)
    export_step(Compound(children=kids, label="faro_lamp"), str(OUT / "faro_assembly.step"))
    # STLs as assembled
    stl = OUT / "stl"
    if stl.exists():
        shutil.rmtree(stl)
    stl.mkdir()
    for name, shape in m.parts.items():
        export_stl(shape, str(stl / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.15)

    # print set
    d = OUT / "print_prototype"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()
    rows, done = [], set()
    for name, shape in m.parts.items():
        if name in dict(NOT_PRINTED):
            export_stl(shape, str(d / f"{name}_REFERENCE_ONLY.stl"), tolerance=0.02, angular_tolerance=0.15)
            continue
        key = "window_diffuser" if name.startswith("window_diffuser") else name
        if key != "window_diffuser" and key in done:
            continue
        done.add(key)
        if key == "window_diffuser":
            # turn it so its window faces up (each sits at its own angle round the tower)
            k = int(name.rsplit("_", 1)[1]) - 1
            _, ang = m.info["windows"][k]
            shape = Rot(-90, 0, 0) * Rot(0, 0, -ang) * shape
        s, (qty, mat, orient, sup, notes) = _print_pose(name, shape)
        fname = name if key == "window_diffuser" else (f"{key}_x{qty}" if qty > 1 else key)
        export_stl(s, str(d / f"{fname}.stl"), tolerance=0.02, angular_tolerance=0.15)
        sz = s.bounding_box().size
        if key == "window_diffuser" and fname != "window_diffuser_1":
            ang = m.info["windows"][int(fname.rsplit("_", 1)[1]) - 1][1]
            side = {0: "front", 90: "right side", 180: "rear", 270: "left side"}.get(round(ang) % 360, f"{ang:g} deg")
            notes = f"As window_diffuser_1; goes behind the {side} window"
        rows.append((fname, qty, mat, orient, sup, sz, notes))

    I = m.info
    bay = I["bayonet"]
    widest = max(rows, key=lambda r: max(r[5].X, r[5].Y))
    tallest = max(rows, key=lambda r: r[5].Z)
    L = ["# Faro looks-like prototype: print notes", "",
         f"Faro lighthouse lamp, Rosso. {I['H']:.1f} mm tall on its felt pad. The STLs here are "
         "turned to their print orientation and sit on the bed at z = 0 (mm). "
         "`faro/output/stl/` has the same parts as assembled.", "",
         "## Parts to print", "",
         "| File | Qty | Material | Orientation | Supports? | Size X x Y x Z | Notes |",
         "|---|---|---|---|---|---|---|"]
    for fname, qty, mat, orient, sup, sz, notes in rows:
        L.append(f"| {fname}.stl | {qty} | {mat} | {orient} | {sup} | {sz.X:.0f} x {sz.Y:.0f} x {sz.Z:.0f} | {notes} |")
    L += ["", "## Not printed", "", "| Part | How it's made |", "|---|---|"]
    for n, how in NOT_PRINTED:
        L.append(f"| {n} ({n}_REFERENCE_ONLY.stl) | {how} |")
    L += ["", "## Render-only / bought-in (not in the print set)", "", "| Item | What to use |", "|---|---|"]
    for n, what in RENDER_ONLY:
        L.append(f"| {n} | {what} |")
    turn = (f"{abs(p.LOCK_TURN_DEG):g} deg {'clockwise' if p.LOCK_TURN_DEG < 0 else 'anticlockwise'} "
            "(seen from above) to the stop")
    if SCREWED:
        order = [
            f"1. Base: melt the {p.SCREWS} {p.SCREW_SIZE} inserts into the bosses; glue on the nameplate.",
            "2. Glue the cream band onto the base top, then the red band, then the tower, all centred "
            "(they stack on flat joints). Glue the knob, and each window diffuser behind its own window "
            "(1 = lowest, on the front, up to 5 = highest, back on the front).",
            "3. Glue the gallery onto the tower top. Stand the lantern glass on the gallery platform, then "
            "lower the frame over it and glue the frame to the gallery.",
            f"4. Glue the finial into the cap. Twist the cap on: lugs down through the 4 slots, turn {turn}.",
            "5. Underneath: battery in the bay, plate on with the 4 screws, felt pad on (the magnets hold it)."]
    else:   # as in the build manual (step 6)
        order = [
            "1. Diffusers into the tower. Through the open top, glue each behind its window with tiny dabs at the "
            "edges only (1 = lowest, on the front, up to 5 = highest, back on the front).",
            "2. Nameplate into its recess on the front of the base.",
            "3. Knob onto the front of the red band, centred.",
            "4. Thread the lights in through the USB-C port at the back of the base and up through the hole in its "
            "top. The battery box stays outside, behind the lamp.",
            "5. Stack and glue the cream band onto the base, then the red band, then the tower, with knob and "
            "nameplate aligned. Pull the lights up as you go.",
            "6. Coil the lights loosely inside the tower so some sit near each window. Keep them all in the tower.",
            "7. Gallery onto the tower top.",
            "8. Lantern. Stand the empty glass on the gallery, lower the frame over it and glue the frame to the "
            "gallery. The lantern stays empty for the brightness test.",
            f"9. Finial into the cap, then twist the cap on: lugs down through the 4 slots, turn {turn}. "
            "Do not glue it.",
            "10. Weight. Tape a few coins low inside the base.",
            "11. Underneath. Glue the base plate into its rebate, then apply the felt, trimmed to size. "
            "No inserts, screws or magnets in the prototype."]
    L += ["", "## Assembly order", "", "See the build manual (faro/output/manual/Faro_Build_Manual.pdf) for "
          "painting and finishing." if not SCREWED else "", *order, "",
          "## Fit checks (from the model)", "",
          (f"* Battery bay {I['battery_bay'][0]:.0f} mm across x {I['battery_bay'][1]:.1f} mm tall: the "
           f"battery has {I['battery_clear']['bay_height_margin']:.1f} mm headroom and clears the screw bosses."
           if SCREWED else
           f"* Hollow base {I['battery_bay'][0]:.0f} mm across x {I['battery_bay'][1]:.1f} mm tall: room for "
           "the coins, and for the fairy-light wire from the rear port to the hole in the top."),
          f"* LED puck: a ledge inside the gallery leaves a Ø{I['gallery_ledge_bore']:.0f} mm hole, so a puck up "
          f"to {p.LED_PUCK_MAX_DIA:g} mm rests at lantern height on {I['puck_rest_width']:.1f} mm of ledge.",
          f"* Walnut under the rounded top edge: at least {p.BASE_TOP_ROUND - __import__('math').hypot(p.BASE_TOP_ROUND - p.BASE_WALL, p.BASE_TOP_ROUND - p.BASE_TOP_WALL):.1f} mm.",
          f"* Cap bayonet: no clash when locked ({bay['locked_clash']:.2f} mm3), lugs pass the slots at entry "
          f"({bay['entry_clash']:.2f} mm3), {bay['lug_overlap_under_lip']:.1f} mm of lug under the lip. "
          f"With the cap off the opening is Ø{I['led_access_dia']:.0f} mm, so the Ø{p.LED_DIA:g} mm LED "
          "module lifts out.",
          f"* Fit clearance {p.FIT_CLEAR:g} mm per side on the bayonet and {p.PLATE_CLEAR:g} mm round the "
          "bottom plate: PLA may need light sanding.",
          f"* The felt stands {I['felt_proud']:.1f} mm proud of the walnut, so the lamp sits on the felt, "
          "not the wood.",
          "",
          "## General", "",
          f"* Widest part: {widest[0]}.stl at {widest[5].X:.0f} mm; tallest: {tallest[0]}.stl at "
          f"{tallest[5].Z:.0f} mm. Any common printer (180 x 180 x 180 mm or more) fits every part.",
          "* Paint the lacquer parts with filler-primer, sanding, then gloss cream / red and a clear coat. "
          "Brass parts: metallic gold over gloss black, or brass-fill filament polished.",
          "* The railing and lantern frame are the most delicate parts; resin gives the crispest result.",
          ""]
    (d / "PRINT_NOTES.md").write_text("\n".join(L) + "\n")
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--draft", action="store_true", help="front + side + underside renders only")
    args = ap.parse_args()
    t0 = time.time()
    m = lamp.build(p)
    if args.draft:
        files = studio.render_views(m, p, OUT / "draft", views=("front", "side"))
        files.append(studio.render_underside(m, p, OUT / "draft" / "faro_underside.png"))
        print(f"Draft done in {time.time() - t0:.0f} s:", *files, sep="\n  ")
        return
    print("Exporting STEP, STLs and the print set...")
    d = final(m)
    print("Rendering...")
    r = OUT / "renders"
    files = studio.render_views(m, p, r, views=("front", "side", "three_quarter", "rear"))
    files.append(studio.render_underside(m, p, r / "faro_underside.png"))
    studio.atelier.contact_sheet(files[:4], r / "faro_overview.png", scale=0.5)
    print(f"Done in {time.time() - t0:.0f} s -> {OUT}  (print set: {d})")


if __name__ == "__main__":
    main()
