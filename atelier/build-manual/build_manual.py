"""
Build the Atelier prototype build manual (PDF), in the same style and
structure as faro/manual/build_manual.py (which this shares its page
furniture with, via manual_common/pdf_page.py).

    python atelier/build-manual/illustrate.py      # render the images first
    python atelier/build-manual/build_manual.py    # -> atelier/build-manual/output/Atelier_Build_Manual.pdf

Content, geometry and part list come from model.py / output/report.md /
output/print_prototype/PRINT_NOTES.md -- never estimated. Every specific
paint or supply PRODUCT (not the generic kind, e.g. "gloss black spray" vs.
a named shade) is marked "proposed" here for Ido to review; see the
SUPPLIES list below. Every page's content is checked against the footer
rule before it's committed to the PDF (see `end_page`) -- a layout bug
fails the build instead of silently printing under the footer.
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
import params as p  # noqa: E402

FONTS = HERE / "fonts"
IMG = HERE / "output" / "images"
OUT = HERE / "output" / "Atelier_Build_Manual.pdf"

common.register_fonts(FONTS)

W, H = common.W, common.H
L, R = common.L, common.R
PAPER, INK, GREY, RED, GOLD, HAIR = common.PAPER, common.INK, common.GREY, common.RED, common.GOLD, common.HAIR
BODY, BODY_S, STAND, CAP, CHECK, NOTE = (common.BODY, common.BODY_S, common.STAND, common.CAP, common.CHECK,
                                          common.NOTE)
FOOTER_SAFE_Y = common.FOOTER_SAFE_Y


def Page(c, section, number):
    """atelier/build-manual's own Page, bound to its footer text and image dirs."""
    return common.Page(c, section, number, footer_text="Atelier, prototype build manual", img_dir=IMG)


def end_page(c, pg, y, label):
    """Check `y` (the lowest point this page's content reached) against the
    footer rule, then advance to the next page. Call this instead of a bare
    c.showPage() at the end of every page-drawing function."""
    pg.check_bounds(y, label)
    c.showPage()


# ---- real dimensions, read from the model (output/report.md / model.py's own
# info dict), not estimated -- used throughout the copy below -----------------
import model  # noqa: E402

_M = model.build(p, visual_only=True)
INFO = _M.info
KNOB_HOLE_DIA = round(p.KNOB_BOSS_DIA + 4 * p.FIT_CLEARANCE, 1)   # body's own knob hole
KNOB_BOSS_DIA = p.KNOB_BOSS_DIA
KNOB_BOSS_LEN = p.KNOB_BOSS_LENGTH
KNOB_SHAFT_BORE = p.KNOB_SHAFT_DIA
FIN_PILOT_DIA = 3.3                                # from output/print_prototype/PRINT_NOTES.md, unchanged by
                                                    # the resin switch (the pilot hole itself doesn't depend on
                                                    # print material)
COLLAR_CLEARANCE = 0.2                              # output/print_prototype/PRINT_NOTES.md: collar friction-fit
WEIGHT_G = 500                                      # output/print_prototype/PRINT_NOTES.md's own estimate,
                                                     # to bring a resin prototype (~180-250 g) towards a
                                                     # believable hand-feel; not the 1.8 kg production target


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
    pg.spaced(W / 2, 70, "OXBLOOD  ·  LOOKS-LIKE PROTOTYPE  ·  SEPTEMBER 2026", size=6.8, color=GREY,
              space=1.9, align="center")
    # No footer on the cover (Page(c, None, None) drew none), so there's no
    # footer rule to guard against here -- unlike every other page below.
    c.showPage()


def before_you_begin(c):
    pg = Page(c, "Before you begin", 2)
    pg.kicker(H - 110, "Introduction")
    pg.title(H - 145, "Before you begin")
    y = pg.para(L, H - 160, 340, "From the box of printed resin parts to a finished prototype, ready to "
                "photograph and shake down.", STAND)
    pg.rule(L, y - 12)
    y = pg.para(L, y - 26, R - L, "Atelier is built from eight printed pieces (the fins print once and go on "
                "three times), finished by hand in two colours and glued together in a set order. Nothing here "
                "is difficult, but each stage needs patience: thin coats of paint, time to cure, and a dry fit "
                "before any glue. Each step ends with a checkpoint; don't move on until it is met.")
    pg.heading(L, y - 22, "Timing")
    y -= 30
    cols = [("Weekend one", "Inspect and dry-fit, prepare the surfaces, prime, and paint the colours."),
            ("The week between", "Let the clear coat harden. It feels dry within hours but needs days to "
             "cure fully."),
            ("Weekend two", "Assemble, weigh it down, and check it stands and photographs well.")]
    cw = (R - L) / 3
    c.setStrokeColor(HAIR)
    c.setLineWidth(0.5)
    c.line(L, y, R, y)
    low = y
    for k, (h_, t) in enumerate(cols):
        x = L + k * cw
        c.setFont("Garamond-Medium", 11)
        c.setFillColor(INK)
        c.drawString(x, y - 16, h_)
        low = min(low, pg.para(x, y - 22, cw - 14, t, BODY_S))
    y = low - 22
    box_top = y
    items = ["Spray outdoors or somewhere very well ventilated, and wear the respirator whenever you spray.",
             "Wear a dust mask or the respirator, and nitrile gloves, when sanding resin: its dust shouldn't be "
             "breathed in or left on skin.",
             "Wear nitrile gloves when mixing or applying epoxy.",
             "Keep sprays and epoxy away from children and pets, and let fumes clear before bringing parts "
             "indoors."]
    pg.heading(L + 14, y - 18, "Safety", color=RED)
    yb = pg.bullets(L + 14, y - 28, R - L - 28, items)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.rect(L, yb - 8, R - L, box_top - (yb - 8), stroke=1, fill=0)
    y = yb - 34
    pg.heading(L, y, "How to use this manual")
    pg.para(L, y - 10, 225, "Work through the seven steps in order. Each part's colour and treatment is listed "
            "on the next page; keep it open while you paint. If something goes wrong, turn to Troubleshooting "
            "at the back: almost every mistake can be sanded out and repainted.")
    y2 = pg.image("front_finished", L + 250, y + 6, width=R - L - 250, caption="The front, finished.")
    end_page(c, pg, min(yb - 34 - 60, y2), "before you begin")


# Part | Qty | Finish | swatch key. Finish is the painted/assembled state (matching
# faro/manual/build_manual.py's PARTS table), not the print material -- every part in
# this set prints in resin (see Step 02 below and README.md's note on resin vs. FDM).
SW = {"oxblood": "#8A1C15", "gold": "#C4A15A", "black": "#1F1D1C"}
PARTS = [
    ("Body", "1", "Oxblood gloss, clear coat", "oxblood"),
    ("Nose cone", "1", "Metallic gold", "gold"),
    ("Fins", "3", "Metallic gold", "gold"),
    ("Grille", "1", "Metallic gold; recess floor behind it masked and painted matt black", "gold"),
    ("Bezel", "1", "Metallic gold", "gold"),
    ("Knob", "1", "Metallic gold; decorative on the prototype, doesn't turn", "gold"),
    ("Collar", "1", "Metallic gold", "gold"),
    ("Foot", "1", "Metallic gold", "gold"),
]

# Every named product below is a PROPOSAL, not a confirmed choice -- flagged for
# Ido's review before print. The generic kind (e.g. "grey filler primer") is not
# in question; the specific product and its compatibility with the other two is.
# All three (primer, colour, clear) are from one system (U-POL) so they're built
# to work together; Step 04 adds a swatch test before the full spray-out regardless.
SUPPLIES_LEFT = [
    "U-POL Isolate Acid #8 etch primer, or U-POL Custom Grey primer-filler (proposed, primer)",
    "Oxblood/deep red basecoat to match #8A1C15, colour-matched by a U-POL or automotive "
    "refinish supplier (proposed, colour, confirm on a swatch, Step 04)",
    "U-POL High Build 1K Clear Lacquer, aerosol (proposed, clear, same system as the primer and colour)",
    "Metallic gold spray, e.g. Rust-Oleum Universal Metallic “Gold” (proposed, for the trim parts, "
    "left uncoated)",
    "Matt black acrylic and a small brush, for the grille recess floor",
    "Wet-and-dry paper, P240 to P1200",
]
SUPPLIES_RIGHT = [
    "Tamiya masking tape, 10 mm",
    "Araldite Rapid epoxy, cocktail sticks",
    f"M4 x 12 mm self-tapping screws, 6 (proposed, for the fins, into their {FIN_PILOT_DIA} mm pilot holes; "
    "epoxy alone is the fallback, see Step 06)",
    f"Steel shot or fishing weights, about {WEIGHT_G} g, for the internal weight (proposed)",
    "Respirator suitable for solvent-borne spray paint, dust mask, nitrile gloves",
    "Craft knife, blu-tack",
    "A spare printed swatch or offcut, for the Step 04 paint test",
]


def parts_and_supplies(c):
    pg = Page(c, "Parts and supplies", 3)
    pg.kicker(H - 110, "Inventory")
    pg.title(H - 145, "Parts and supplies")
    y = pg.table(L, H - 172, ["Part", "Qty", "Finish"], [r[:3] for r in PARTS], [90, 40, R - L - 130],
                 swatch=[SW[r[3]] for r in PARTS], style=BODY_S)
    pg.heading(L, y - 26, "Supplies")
    y1 = pg.bullets(L, y - 38, (R - L) / 2 - 10, SUPPLIES_LEFT)
    y2 = pg.bullets(L + (R - L) / 2 + 6, y - 38, (R - L) / 2 - 10, SUPPLIES_RIGHT)
    y3 = pg.para(L, min(y1, y2) - 14, R - L, "Every specific product above is proposed, not confirmed: the "
                 "primer, colour and clear are one compatible system (Step 04 still opens with a swatch test "
                 "before the full spray-out), but the exact colour match and the clear's cure schedule need "
                 "checking against a real can before you commit to it.", NOTE)
    end_page(c, pg, y3, "parts and supplies")


def step1_inspect(c):
    pg = Page(c, "Step 1", 4)
    pg.kicker(H - 110, "Step 01")
    pg.title(H - 145, "Inspect and dry-fit")
    y = pg.para(L, H - 160, 340, "Check every part and fit them together without glue. Paint adds thickness, "
                "so tight fits only get tighter.", STAND)
    pg.rule(L, y - 12)
    top = y - 30
    img_w = 270
    img_y = pg.image("01_exploded_resin", L, top, width=img_w, height=top - FOOTER_SAFE_Y - 10, align="center")
    x = L + img_w + 22
    yy = pg.steps(x, top, R - x, [
        "Tick off every part against the inventory. Look for cracks, warping or resin flash.",
        "Stand the collar on the foot, then hold the body over the collar's spigot: it should sit "
        "straight, without forcing.",
        f"Press the knob's boss (its own moulded peg, {KNOB_BOSS_DIA:.0f} mm across, {KNOB_BOSS_LEN:.0f} mm "
        f"long) into the body's knob hole ({KNOB_HOLE_DIA:.1f} mm across, {(KNOB_HOLE_DIA - KNOB_BOSS_DIA) / 2:.1f} "
        "mm clearance all round). It should push in with light resistance and no rocking.",
        "Hold the grille in its recess, then the bezel over its edge. Both should sit flush, without a gap "
        "or a lip proud of the body.",
        "Dry-fit each fin against the body: the flat root should sit flush against the hull with its "
        f"pilot holes ({FIN_PILOT_DIA} mm) aligned to the body's own.",
        "Stand the nose cone on the body's top rim: it should sit centred and level.",
        "Stand the whole dry stack where it would live, and judge size and proportions."],
        style=BODY_S, gap=5)
    end_page(c, pg, min(yy, img_y) - 10, "step 1")


def step2_prepare(c):
    pg = Page(c, "Step 2", 5)
    pg.kicker(H - 110, "Step 02")
    pg.title(H - 145, "Prepare the surfaces")
    y = pg.para(L, H - 160, 360, "Clean, smooth surfaces are what make the paint look expensive.", STAND)
    pg.rule(L, y - 12)
    y = pg.steps(L, y - 30, R - L, [
        "Wash all parts in warm soapy water, rinse, and leave to dry fully.",
        "Trim any support marks with a craft knife, cutting away from yourself.",
        "Put on a dust mask or the respirator, and gloves. Sand visible surfaces with P240 to flatten marks, "
        "then P400 to smooth.",
        "Wipe the dust off with a barely damp cloth and let dry."])
    y = pg.image("02_printed_parts", L + 60, y - 10, width=R - L - 120,
                 caption="Every printed part, as it arrives in plain white resin.")
    box_top = y - 18
    pg.heading(L + 14, box_top - 18, "Handle with care", color=RED)
    yb = pg.bullets(L + 14, box_top - 28, R - L - 28, [
        "<b>Grille:</b> the honeycomb webs are fine and can snap; only remove support marks from the flat "
        "back, never press on the front face.",
        "<b>Bezel:</b> its edge is thin all the way round; sand it flat on a board rather than freehand, so "
        "it doesn't go out of round.",
        "<b>Fins:</b> the trailing edge tapers to almost nothing; support it in your hand while you sand so "
        "it doesn't flex or crack."])
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.rect(L, yb - 8, R - L, box_top - (yb - 8), stroke=1, fill=0)
    y3 = pg.checkpoint(yb - 30, "every part is clean, dry and dust-free, with no support marks left on the "
                        "surfaces that show.")
    end_page(c, pg, y3, "step 2")


def step3_prime(c):
    pg = Page(c, "Step 3", 6)
    pg.kicker(H - 110, "Step 03")
    pg.title(H - 145, "Prime")
    y = pg.para(L, H - 160, 360, "Primer fills fine layer lines and shows every flaw. This is where the final "
                "finish is really made.", STAND)
    pg.rule(L, y - 12)
    y = pg.steps(L, y - 30, R - L, [
        "Mount parts on a tube, bottle or cocktail sticks with blu-tack, so you can reach all round without "
        "touching.",
        "Choose a dry, still day, around 15 to 25°C. Shake the primer for two to three minutes.",
        "Spray light coats from 25 to 30 cm, starting and finishing each pass off the part.",
        "Let it dry, then sand with P400, wearing the dust mask. Repeat until the surfaces look smooth under "
        "a bright light.",
        "Prime every part, body included."])
    y = pg.para(L, y - 8, R - L, "<b>Drying times.</b> Typically touch-dry in 15 to 30 minutes, ready for the "
                "next coat after about 30 minutes, and ready to sand after at least an hour. Brands vary, so "
                "check the can.", NOTE)
    y = pg.image("03_priming", L, y - 16, width=R - L, caption="Every part mounted for priming.")
    y3 = pg.checkpoint(y - 26, "every part is an even grey, with no layer lines, pits or bare spots under a "
                        "bright light.")
    end_page(c, pg, y3, "step 3")


def step4_paint(c):
    pg = Page(c, "Step 4", 7)
    pg.kicker(H - 110, "Step 04")
    pg.title(H - 145, "Paint")
    y = pg.para(L, H - 160, 400, "Two colours, so there's little masking between them. Tape only the surfaces "
                "that will be glued, and test the system on a swatch before you commit the real parts.", STAND)
    pg.rule(L, y - 12)
    rows = [("Oxblood gloss", "body"),
            ("Metallic gold", "nose cone, fin x3, grille, bezel, knob, collar, foot"),
            ("Matt black", "grille recess floor (on the body, masked)")]
    y = pg.table(L, y - 24, ["Colour", "Parts"], rows, [150, R - L - 150],
                 swatch=[SW["oxblood"], SW["gold"], SW["black"]])
    y = pg.image("04_paint_groups", L, y - 12, width=R - L)
    col = (R - L) / 2 - 10
    pg.heading(L, y - 20, "Swatch test first")
    ym = pg.para(L, y - 32, col, "Spray the primer, oxblood colour and clear on a spare printed offcut in "
                 "that order, exactly as you plan to spray the body, and let it cure fully (see Step 05's "
                 "timings). Some colours wrinkle or lift under some clears; if the swatch stays smooth and hard, "
                 "carry on.", BODY_S)
    pg.heading(L, ym - 18, "Mask before painting")
    ym = pg.bullets(L, ym - 30, col, [
        "The body's cone-joint rim and collar spigot",
        "The grille and bezel's back edges, where they seat in the recess",
        "The back of the knob's boss",
        "Each fin's flat root, where it glues to the hull"], gap=2)
    x2 = L + (R - L) / 2 + 10
    pg.heading(x2, y - 20, "Spraying")
    ys = pg.steps(x2, y - 32, R - x2, [
        "Three or four light coats, 25 to 30 cm away.",
        "On the grille, spray at an angle into the honeycomb so the inner walls are covered.",
        "If dust or a run appears, let it dry, sand with P1200 and respray lightly.",
        "Mask the grille recess floor once the body's gold... " if False else
        "Once the body's oxblood coat is dry, mask the honeycomb opening and hand-brush the recess floor "
        "matt black; wipe the raised surround clean before it dries."], style=BODY_S, gap=3, num_w=20)
    ys = pg.para(x2, ys - 4, R - x2, "<b>Drying times.</b> Typically touch-dry in 15 to 30 minutes, with the "
                 "next coat after 15 to 30 minutes. Check the can.", NOTE)
    y3 = pg.para(L, min(ym, ys) - 10, R - L, "The clear coat is next, in Step 05; this step's checkpoint "
                 "comes after it.", CAP)
    end_page(c, pg, y3, "step 4")


def step4b_reference(c):
    pg = Page(c, "Step 4, continued", 8)
    pg.kicker(H - 110, "Step 04, continued")
    pg.title(H - 145, "Colour reference")
    pg.rule(L, H - 160)
    y = pg.para(L, H - 176, R - L, "Every part, gold trim included, is painted here in Step 04. These views "
                "show how the finished colours should look once every coat is on.", BODY_S)
    top = y - 20
    checkpoint_reserve = 66.0
    col_gap, row_gap = 20.0, 16.0
    col_w = (R - L - col_gap) / 2
    avail_h = top - FOOTER_SAFE_Y - checkpoint_reserve
    row_h = (avail_h - row_gap) / 2
    row1_top = top - row_h - row_gap
    low = row1_top
    views = (("04_view_front", "Front"), ("04_view_side", "Side"),
             ("04_view_rear", "Rear"), ("04_view_three_quarter", "Three-quarter"))
    for i, (nm, cap) in enumerate(views):
        rr, cidx = divmod(i, 2)
        x = L + cidx * (col_w + col_gap)
        row_top = top if rr == 0 else row1_top
        low = min(low, pg.image(nm, x, row_top, width=col_w, height=row_h, align="center", caption=cap))
    y3 = pg.checkpoint(low - 14, "every part is evenly coloured with no bare patches or runs, and the masking "
                        "tape is off.")
    end_page(c, pg, y3, "step 4 continued")


def step5_6(c, number):
    """Steps 05 and 06 share a page, as Faro does with its own Steps 5 and 6."""
    pg = Page(c, "Steps 5 and 6", number)
    pg.kicker(H - 110, "Step 05")
    pg.title(H - 145, "Clear coat and cure")
    y = pg.para(L, H - 160, 400, "The gold trim is left uncoated (a clear coat dulls metallic paint), but "
                "the body's oxblood gloss is clear-coated for the lacquer look.", STAND)
    pg.rule(L, y - 12)
    y = pg.steps(L, y - 30, R - L, [
        "Wait at least 24 hours after the oxblood colour coat.",
        "Spray 2 to 3 light coats on the body only.",
        "Leave it warm, dry and dust-free for two to three days. Paint feels dry long before the clear is "
        "fully hard.",
        "Optional: once fully hard, polish the body with car polishing compound."], style=BODY_S, gap=3)
    y = pg.para(L, y - 6, R - L, "<b>Drying times.</b> Typically touch-dry in 15 to 30 minutes, with the next "
                "coat after 15 to 30 minutes, and fully cured in a few days at room temperature. Check the "
                "can.", NOTE)
    y = pg.checkpoint(y - 16, "the body's gloss is even and hard: a fingernail pressed on a hidden spot "
                       "leaves no mark, and the gold trim parts are unclouded.")
    pg.kicker(y - 34, "Step 06")
    pg.title(y - 68, "Assemble")
    y = pg.para(L, y - 82, 400, "Araldite Rapid gives about five minutes to position a joint. Mix small "
                "amounts, one joint at a time, and hold or tape each joint as it sets.", STAND)
    pg.rule(L, y - 10)
    y = pg.bullets(L, y - 26, R - L, [
        "Wait about 20 to 30 minutes before handling a glued joint or starting the next one.",
        "Epoxy reaches full strength the next day: leave the finished prototype overnight before lifting it "
        "by the nose cone or testing its stability.",
        "Dry-fit each joint just before you glue it, and wipe off any squeeze-out with a cocktail stick "
        "before it sets."], style=BODY_S)
    pg.heading(L, y - 22, "Order")
    y4 = pg.para(L, y - 34, R - L, "Front details first, then the fins, then a dry-fit and unweighted tip "
                 "test before the weight goes in, then seal the base and cap the nose: grille, bezel, knob, "
                 "fins, dry-fit tip test, weight, collar, foot, nose cone. The weight has to go in before the "
                 "collar, while the body's underside is still open.", BODY_S)
    end_page(c, pg, y4, "step 5 and 6")


IMG_ASPECT = 1000 / 800   # assembly step renders are 1000x800


def assembly_rows(pg, y_top, rows, first, reserve_below=0.0):
    """Lays out up to 4 numbered rows (image left, step text right), each
    image scaled to fit an even share of whatever vertical space is left on
    the page -- not a fixed guessed size -- so a page never overflows past
    the footer regardless of how many rows it holds or whether a checkpoint
    follows. Returns the lowest y reached."""
    c = pg.c
    n = len(rows)
    row_overhead = 19.0                    # gap image-bottom -> divider (9) + divider -> next row (10)
    available = y_top - FOOTER_SAFE_Y - reserve_below
    img_h = min(max(available / n - row_overhead, 60.0), 150.0)
    img_w = img_h * IMG_ASPECT
    y = y_top
    for k, (title, text, imgs) in enumerate(rows):
        num = first + k
        row_top = y
        low = pg.image(imgs[0], L, row_top, width=img_w, height=img_h, align="center")
        x = L + img_w + 22
        c.setFont("Garamond", 20)
        c.setFillColor(RED)
        c.drawString(x, row_top - 17, f"{num:02d}")
        c.setFont("Garamond-Medium", 11.5)
        c.setFillColor(INK)
        c.drawString(x + 32, row_top - 15, title)
        ty = pg.para(x + 32, row_top - 22, R - x - 32, text, BODY_S)
        y = min(low, ty) - 9
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.4)
        c.line(L, y, R, y)
        y -= 10
    return y


ASSEMBLY_1 = [
    ("Grille", "The grille recess floor was painted matt black in Step 04; check it's fully dry, then glue "
     "the grille into the recess.", ["06_01_grille"]),
    ("Bezel", "Over the grille's edge, into the same recess.", ["06_02_bezel"]),
    ("Knob", f"Glue the knob's {KNOB_BOSS_DIA:.0f} mm boss into the body's own knob hole. On the prototype it "
     "is decorative and doesn't turn.", ["06_03_knob"]),
    ("Fins", f"Align each fin's pilot holes ({FIN_PILOT_DIA} mm) with the body's, then fix with M4 "
     "self-tapping screws from inside, or epoxy alone if you'd rather not drill.", ["06_04_fins"]),
]
ASSEMBLY_2 = [
    ("Dry-fit tip test", "Once the fin epoxy has set (ideally overnight), dry-fit the collar and foot (no "
     "glue yet) and stand the prototype on the fins and foot. Nudge it gently from the side and note on the "
     "test record how little it takes to tip, unweighted. Then take the collar and foot off again.",
     ["06_04b_dryfit_tip"]),
    ("Weight", f"Glue about {WEIGHT_G} g of steel shot low inside the body, through the open bottom, clear "
     "of the knob boss and fin screws.", ["06_05_weight"]),
    ("Collar", "Friction-fits onto the body's underside spigot (0.2 mm clearance); glue it in place, sealing "
     "the weight inside.", ["06_06_collar"]),
    ("Foot", "Glue centred under the collar.", ["06_07_foot"]),
    ("Nose cone", "Glue onto the body's top rim, centred.", ["06_08_nose_cone"]),
]


def assembly_page_1(c, number):
    pg = Page(c, "Step 6, assembly", number)
    pg.kicker(H - 110, "Step 06, assembly, 1 of 2")
    pg.title(H - 145, "Assembly order", size=26)
    pg.rule(L, H - 158)
    y = assembly_rows(pg, H - 176, ASSEMBLY_1, 1)
    end_page(c, pg, y, "assembly page 1")


def assembly_page_2(c, number):
    pg = Page(c, "Step 6, assembly", number)
    pg.kicker(H - 110, "Step 06, assembly, 2 of 2")
    pg.title(H - 145, "Assembly, continued", size=26)
    pg.rule(L, H - 158)
    checkpoint_text = ("the glue has set overnight, the fins are firm with no flex, and the prototype stands "
                        "level on the foot without rocking.")
    reserve = 70.0
    y = assembly_rows(pg, H - 176, ASSEMBLY_2, 5, reserve_below=reserve)
    y3 = pg.checkpoint(y - 4, checkpoint_text)
    end_page(c, pg, y3, "assembly page 2")


def step7_stability(c, number):
    pg = Page(c, "Step 7", number)
    pg.kicker(H - 110, "Step 07")
    pg.title(H - 145, "Stability check and photograph")
    y = pg.para(L, H - 160, R - L, "The model's own numbers describe the production part, not this "
                "hand-glued, hand-weighted resin one, so this step is a physical test, not a rendered "
                "prediction. The unweighted comparison was back in Step 06; this is the weighted check.", STAND)
    pg.rule(L, y - 12)
    colw = 260
    pg.heading(L, y - 34, "Tip test")
    yy = pg.steps(L, y - 46, colw, [
        "Stand the finished prototype on a flat, level surface, resting on its three fin tips and the "
        "centre foot.",
        "Nudge it gently from the side at about knob height and see how much it takes to tip.",
        "Try it on a soft surface (a rug or cushion) too, and note whether it's noticeably less stable."],
        style=BODY_S, gap=3)
    pg.heading(L, yy - 18, "What good looks like")
    yy = pg.bullets(L, yy - 30, colw, [
        "It resists a firm, deliberate nudge and only tips under a hard knock.",
        "It stands level on all three fins and the foot, without rocking.",
        "It feels reassuringly solid to pick up, not hollow."])
    pg.heading(L, yy - 18, "Photographs")
    yy = pg.bullets(L, yy - 30, colw, [
        "Two sets: plain backdrop, and one styled shelf scene.",
        "Front, side, three-quarter, rear, grille close-up, underside.",
        "Natural daylight if you can; note the light source either way."])
    x2 = L + colw + 24
    rcw = R - x2
    y2 = pg.image("04_view_three_quarter", x2, y - 20, width=rcw, caption="Three-quarter, for reference.")
    yi = pg.image("07_underside", x2, y2 - 14, width=rcw * 0.72,
                   caption="Underside: fins and foot take the weight.")
    y3 = pg.checkpoint(min(yy, yi) - 20, "it passes the weighted tip test, the test record is filled in "
                        "(unweighted note from Step 06 included), and both photo sets are taken.")
    end_page(c, pg, y3, "step 7")


TROUBLESHOOTING = [
    ("Knob boss won't seat, or rocks", f"Sand the boss lightly with P400 and test again; it should press into "
     f"the body's {KNOB_HOLE_DIA:.1f} mm hole with light resistance, not force."),
    ("Fin sits proud, or rocks", f"Check the pilot holes are aligned before driving the screws; a fin that's "
     "still proud after gluing can be sanded flush at its root and touched up."),
    ("Paint run or sag", "Let it harden, sand flat with P1200 and spray a light coat over it."),
    ("Rough, bumpy gloss (orange peel)", "Sand gently with P1200 and polish, or add another light clear "
     "coat. Next time, lighter coats."),
    ("Dust specks", "Once hard, sand the speck with P1200 and respray lightly on a still day."),
    ("Clear wrinkles, lifts or stays soft", "Let it harden as far as it will, then sand back and respray "
     "the colour. Next time, run the Step 04 swatch test all the way through the clear before touching the "
     "real body."),
    ("Grille recess paint bleeds onto the gold rim", "Mask right up to the honeycomb opening before brushing "
     "the black on, and wipe any bleed off with a cocktail stick while it's still wet."),
    ("Steel shot rattles", "Use more epoxy, not less, and let it fully gel with the body tipped so the shot "
     "settles low and flat before the collar goes on."),
    ("Prototype still tips easily with the weight fitted", "Add more shot, kept as low and central as "
     "the collar allows, and note the extra weight for the ODM."),
]


def troubleshooting(c, number):
    pg = Page(c, "Troubleshooting", number)
    pg.kicker(H - 110, "Reference")
    pg.title(H - 145, "Troubleshooting")
    y = pg.para(L, H - 160, 380, "Almost every problem is recoverable. Let paint harden fully before sanding "
                "or recoating.", STAND)
    pg.rule(L, y - 12)
    y = pg.table(L, y - 30, ["Problem", "Fix"], TROUBLESHOOTING, [190, R - L - 190], style=BODY_S)
    y2 = pg.image("TS_fin_root", L + 70, y - 14, width=200, align="left", caption="A fin's root, flush "
                  "against the body: what a good fit looks like.")
    end_page(c, pg, y2, "troubleshooting")


def test_record(c, number):
    pg = Page(c, "Record", number)
    pg.kicker(H - 110, "Reference")
    pg.title(H - 145, "Test record")
    y = pg.para(L, H - 160, 380, "Write down what you learn before changing anything. It becomes the brief "
                "for the industrial designer and ODM.", STAND)
    pg.rule(L, y - 12)
    y -= 36
    for lab in ("Total weight fitted", "Steel shot used", "Paint system used"):
        c.setFont("Garamond", 10.5)
        c.setFillColor(INK)
        c.drawString(L, y, lab)
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.5)
        c.line(L + 150, y - 2, R, y - 2)
        y -= 24
    y -= 8
    scales = [("Fit", "Loose", "About right", "Tight"), ("Finish", "Rough", "Good", "Excellent"),
              ("Stability, unweighted (Step 06)", "Tips easily", "Some resistance", "Solid"),
              ("Stability, weighted (Step 07)", "Tips easily", "Some resistance", "Solid"),
              ("Weight and feel", "Too light", "About right", "Too heavy"),
              ("Proportions vs. the concept", "Off", "Close", "Spot on")]
    for row in scales:
        c.setFont("Garamond", 10.5)
        c.setFillColor(INK)
        c.drawString(L, y, row[0])
        for k, opt in enumerate(row[1:]):
            x = L + 150 + k * 115
            c.setStrokeColor(GOLD)
            c.setLineWidth(0.6)
            c.circle(x + 4, y + 3.5, 4, stroke=1, fill=0)
            c.setFillColor(INK)
            c.drawString(x + 14, y, opt)
        y -= 22
    pg.heading(L, y - 12, "Notes for the industrial designer and ODM")
    y -= 24
    for k in range(5):
        c.setStrokeColor(HAIR)
        c.line(L, y - k * 20, R, y - k * 20)
    y -= 5 * 20 + 18
    pg.heading(L, y, "Before you finish")
    y -= 18
    for t in ("Glue fully cured (overnight or longer)", "Stands level without rocking",
              "Unweighted tip test noted (Step 06)", "Weighted tip test done (Step 07)",
              "Photos taken, both sets", "Changes noted for prototype two"):
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.6)
        c.rect(L, y - 1, 8, 8, stroke=1, fill=0)
        c.setFont("Garamond", 10.5)
        c.setFillColor(INK)
        c.drawString(L + 16, y, t)
        y -= 20
    end_page(c, pg, y, "test record")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=A4)
    c.setTitle("Atelier, prototype build manual")
    c.setAuthor("Bathsheva London")
    c.setSubject("Oxblood, looks-like prototype")
    for fn in (cover, before_you_begin, parts_and_supplies, step1_inspect, step2_prepare, step3_prime,
               step4_paint, step4b_reference):
        fn(c)
    step5_6(c, 9)
    assembly_page_1(c, 10)
    assembly_page_2(c, 11)
    step7_stability(c, 12)
    troubleshooting(c, 13)
    test_record(c, 14)
    c.save()
    print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
