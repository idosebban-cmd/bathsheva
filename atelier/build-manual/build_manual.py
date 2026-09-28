"""
Build the Atelier prototype build manual (PDF), in the same style and
structure as faro/manual/build_manual.py (which this shares its page
furniture with, via manual_common/pdf_page.py).

    python atelier/build-manual/illustrate.py      # render the images first
    python atelier/build-manual/build_manual.py    # -> atelier/build-manual/output/Atelier_Build_Manual.pdf

CHECKPOINT BUILD: this currently wires up only the cover, parts and
supplies, and the first page of Step 06 (assembly), for review before the
rest of the manual (steps 02-05, 07, troubleshooting, record) is written.

Content, geometry and part list come from model.py / output/report.md /
output/print_prototype/PRINT_NOTES.md -- never estimated. Every specific
paint or supply PRODUCT (not the generic kind, e.g. "gloss black spray" vs.
a named shade) is marked "proposed" here for Ido to review; see the
SUPPLIES list below.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from manual_common import pdf_page as common  # noqa: E402

FONTS = HERE / "fonts"
IMG = HERE / "output" / "images"
OUT = HERE / "output" / "Atelier_Build_Manual.pdf"
JPG = HERE / "output" / ".jpg"

common.register_fonts(FONTS)

W, H = common.W, common.H
L, R = common.L, common.R
PAPER, INK, GREY, RED, GOLD, HAIR = common.PAPER, common.INK, common.GREY, common.RED, common.GOLD, common.HAIR
BODY, BODY_S, STAND, CAP, CHECK, NOTE = (common.BODY, common.BODY_S, common.STAND, common.CAP, common.CHECK,
                                          common.NOTE)


def Page(c, section, number):
    """atelier/build-manual's own Page, bound to its footer text and image dirs."""
    return common.Page(c, section, number, footer_text="Atelier, prototype build manual", img_dir=IMG, jpg_dir=JPG)


# ---- the pages ------------------------------------------------------------------
def cover(c):
    pg = Page(c, None, None)
    pg.mark(W / 2, H - 70, 1.2)
    pg.spaced(W / 2, H - 92, "BATHSHEVA LONDON", size=7.6, space=2.6, align="center")
    pg.image("00_hero", W / 2 - 130, H - 120, width=260)
    c.setFont("Garamond", 54)
    c.setFillColor(INK)
    c.drawCentredString(W / 2, 190, "Atelier")
    c.setFont("Garamond-Italic", 15)
    c.setFillColor(GREY)
    c.drawCentredString(W / 2, 166, "Prototype build manual")
    pg.rule(W / 2 - 25, 150, 50)
    pg.spaced(W / 2, 70, "OXBLOOD  ·  LOOKS-LIKE PROTOTYPE  ·  SEPTEMBER 2026", size=6.8, color=GREY, space=1.9,
              align="center")


# Part | Qty | Finish | swatch key. Finish is the painted/assembled state (matching
# faro/manual/build_manual.py's PARTS table), not the print material -- every part in
# this set prints in resin (see the note on resin vs. FDM in atelier/build-manual/README.md).
SW = {"oxblood": "#8A1C15", "gold": "#C4A15A", "black": "#1F1D1C"}
PARTS = [
    ("body", "1", "Oxblood gloss, clear coat", "oxblood"),
    ("nose_cone", "1", "Metallic gold", "gold"),
    ("fin_x3", "3", "Metallic gold", "gold"),
    ("grille", "1", "Metallic gold; recess floor behind it masked and painted matt black", "gold"),
    ("bezel", "1", "Metallic gold", "gold"),
    ("knob", "1", "Metallic gold; decorative on the prototype, glued on a dowel, doesn't turn", "gold"),
    ("collar", "1", "Metallic gold", "gold"),
    ("foot", "1", "Metallic gold", "gold"),
]

# Every named product below is a PROPOSAL, not a confirmed choice -- flagged for
# Ido's review before print. The generic kind (e.g. "grey filler primer") is not
# in question; the specific product/shade is.
SUPPLIES_LEFT = [
    "Grey filler primer, e.g. Rust-Oleum Automotive Primer (proposed)",
    "Oxblood/deep red gloss spray to match #8A1C15, e.g. Rust-Oleum Universal "
    "Gloss “Berry Red” (proposed -- test against a printed swatch first)",
    "Metallic gold spray, e.g. Rust-Oleum Universal Metallic “Gold” (proposed)",
    "Clear lacquer (gloss)",
    "Matt black acrylic and a small brush, for the grille recess floor",
    "Wet-and-dry paper, P240 to P1200",
]
SUPPLIES_RIGHT = [
    "Tamiya masking tape, 10 mm",
    "Araldite Rapid epoxy, cocktail sticks",
    "M4 x 12 mm self-tapping screws, 6 (proposed -- for the fins; epoxy alone is the "
    "fallback, see Step 06)",
    "6 mm wooden dowel, a short length cut to size (proposed -- for the knob shaft)",
    "Steel shot or fishing weights, about 500 g, for the internal ballast (proposed)",
    "Respirator, dust mask, nitrile gloves",
    "Craft knife, blu-tack",
]


def parts_and_supplies(c):
    pg = Page(c, "Parts and supplies", 3)
    pg.kicker(H - 110, "Inventory")
    pg.title(H - 145, "Parts and supplies")
    y = pg.table(L, H - 172, ["Part", "Qty", "Finish"], [r[:3] for r in PARTS], [90, 40, R - L - 130],
                 swatch=[SW[r[3]] for r in PARTS], style=BODY_S)
    pg.heading(L, y - 26, "Supplies")
    pg.bullets(L, y - 38, (R - L) / 2 - 10, SUPPLIES_LEFT)
    pg.bullets(L + (R - L) / 2 + 6, y - 38, (R - L) / 2 - 10, SUPPLIES_RIGHT)
    pg.para(L, 70, R - L, "Every specific product above is proposed, not confirmed: check it against a "
            "printed test piece before committing to a full spray-out.", NOTE)


ASSEMBLY_1 = [
    ("Grille", "The grille recess floor was painted matt black in Step 04 (see Parts and supplies); "
     "check it's fully dry, then glue the grille into the recess.", ["06_01_grille"]),
    ("Bezel", "Over the grille's edge, into the same recess.", ["06_02_bezel"]),
    ("Knob", "Glue a short length of 6 mm dowel into the body's shaft hole, then glue the knob onto it, "
     "centred below the grille. On the prototype it is decorative and doesn't turn.", ["06_03_knob"]),
]
IMG_W, IMG_H = 240, 260


def assembly_rows(pg, y, rows, first):
    c = pg.c
    for k, (title, text, imgs) in enumerate(rows):
        n = first + k
        low = pg.image(imgs[0], L, y, width=IMG_W, height=IMG_H, align="center")
        x = L + IMG_W + 22
        c.setFont("Garamond", 20)
        c.setFillColor(RED)
        c.drawString(x, y - 17, f"{n:02d}")
        c.setFont("Garamond-Medium", 11.5)
        c.setFillColor(INK)
        c.drawString(x + 32, y - 15, title)
        ty = pg.para(x + 32, y - 22, R - x - 32, text, BODY_S)
        y = min(low, ty) - 9
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.4)
        c.line(L, y, R, y)
        y -= 10
    return y


def assembly_page_1(c, number):
    pg = Page(c, "Step 6, assembly", number)
    pg.kicker(H - 110, "Step 06, assembly, 1 of 3")
    pg.title(H - 145, "Assembly order", size=26)
    pg.rule(L, H - 158)
    assembly_rows(pg, H - 176, ASSEMBLY_1, 1)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=A4)
    c.setTitle("Atelier, prototype build manual")
    c.setAuthor("Bathsheva London")
    c.setSubject("Oxblood, looks-like prototype")
    for fn in (cover, parts_and_supplies):
        fn(c)
        c.showPage()
    assembly_page_1(c, 4)
    c.showPage()
    c.save()
    print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
