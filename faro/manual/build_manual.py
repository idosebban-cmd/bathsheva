"""
Build the Faro prototype build manual (PDF) from the reference text and the
rendered illustrations.

    python faro/manual/illustrate.py      # render the images first
    python faro/manual/build_manual.py    # -> faro/output/manual/Faro_Build_Manual.pdf

Text, step order and structure follow faro/reference/Faro_Build_Manual.pdf;
the photographs are replaced by renders of the model. Calm editorial layout:
EB Garamond throughout, lots of white space, fine gold rules.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
IMG = HERE.parent / "output" / "manual" / "images"
OUT = HERE.parent / "output" / "manual" / "Faro_Build_Manual.pdf"
JPG = HERE.parent / "output" / "manual" / ".jpg"

pdfmetrics.registerFont(TTFont("Garamond", str(FONTS / "EBGaramond-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Garamond-Italic", str(FONTS / "EBGaramond-Italic.ttf")))
pdfmetrics.registerFont(TTFont("Garamond-Medium", str(FONTS / "EBGaramond-Medium.ttf")))
pdfmetrics.registerFontFamily("Garamond", normal="Garamond", italic="Garamond-Italic", bold="Garamond-Medium")

W, H = A4
L, R = 64, W - 64                       # text block
PAPER = HexColor("#F8F4EC")
INK = HexColor("#2B2420")
GREY = HexColor("#6E5F52")
RED = HexColor("#8A1C15")
GOLD = HexColor("#B08A3E")
HAIR = HexColor("#D8CDBC")

BODY = ParagraphStyle("body", fontName="Garamond", fontSize=10.8, leading=15, textColor=INK, alignment=TA_LEFT)
BODY_S = ParagraphStyle("bodys", parent=BODY, fontSize=9.8, leading=13.4)
STAND = ParagraphStyle("stand", fontName="Garamond-Italic", fontSize=14.5, leading=19.5, textColor=GREY)
CAP = ParagraphStyle("cap", fontName="Garamond-Italic", fontSize=9, leading=11.5, textColor=GREY)
CHECK = ParagraphStyle("check", fontName="Garamond-Italic", fontSize=10.6, leading=14.2, textColor=INK)
NOTE = ParagraphStyle("note", fontName="Garamond", fontSize=9.4, leading=12.6, textColor=GREY)


# ---- drawing helpers ------------------------------------------------------------
class Page:
    def __init__(self, c, section, number):
        self.c = c
        c.setFillColor(PAPER)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        if section:
            self.header(section)
        if number:
            self.footer(number)

    def spaced(self, x, y, text, size=7.6, color=INK, font="Garamond-Medium", space=2.2, align="left"):
        c = self.c
        c.setFont(font, size)
        c.setFillColor(color)
        w = pdfmetrics.stringWidth(text, font, size) + space * (len(text) - 1)
        if align == "right":
            x -= w
        elif align == "center":
            x -= w / 2
        c.drawString(x, y, text, charSpace=space)
        return w

    def mark(self, x, y, s=1.0):
        """A small gold sunburst, as in the reference header."""
        import math
        c = self.c
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.6)
        for k in range(9):
            a = math.radians(20 + k * 17.5)
            c.line(x + 3.2 * s * math.cos(a), y + 3.2 * s * math.sin(a), x + 7 * s * math.cos(a),
                   y + 7 * s * math.sin(a))
        c.line(x - 9 * s, y, x + 9 * s, y)

    def header(self, section):
        c = self.c
        self.mark(L + 7, H - 47)
        self.spaced(L + 22, H - 50, "BATHSHEVA LONDON", size=7.4, space=2.4)
        self.spaced(R, H - 50, section.upper(), size=7.2, color=GREY, space=2.2, align="right")
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.5)
        c.line(L, H - 60, R, H - 60)

    def footer(self, n):
        c = self.c
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.5)
        c.line(L, 52, R, 52)
        c.setFont("Garamond-Italic", 8.8)
        c.setFillColor(GREY)
        c.drawString(L, 38, "Faro, prototype build manual")
        c.drawRightString(R, 38, str(n))

    def kicker(self, y, text):
        self.spaced(L, y, text.upper(), size=8, color=RED, space=2.6)

    def title(self, y, text, size=31):
        c = self.c
        c.setFont("Garamond", size)
        c.setFillColor(INK)
        c.drawString(L - 1, y, text)

    def para(self, x, y_top, width, text, style=BODY):
        p = Paragraph(text, style)
        w, h = p.wrap(width, 1000)
        p.drawOn(self.c, x, y_top - h)
        return y_top - h

    def rule(self, x, y, w=62, color=GOLD, width=0.7):
        self.c.setStrokeColor(color)
        self.c.setLineWidth(width)
        self.c.line(x, y, x + w, y)

    def heading(self, x, y, text, color=INK):
        self.spaced(x, y, text.upper(), size=7.6, color=color, space=2.3)

    def steps(self, x, y_top, width, items, style=BODY, gap=5, num_w=26):
        y = y_top
        for i, t in enumerate(items, 1):
            p = Paragraph(t, style)
            w, h = p.wrap(width - num_w, 1000)
            self.c.setFont("Garamond", style.fontSize + 0.6)
            self.c.setFillColor(RED)
            self.c.drawString(x, y - style.fontSize - 0.5, f"{i:02d}")
            p.drawOn(self.c, x + num_w, y - h)
            y -= h + gap
        return y

    def checkpoint(self, y_top, text, x=L, width=R - L):
        """The line that ends each step: when it's safe to move on."""
        self.rule(x, y_top, 28)
        self.spaced(x, y_top - 14, "READY TO MOVE ON WHEN", size=7.2, color=RED, space=2.2)
        return self.para(x, y_top - 20, width, text, CHECK)

    def bullets(self, x, y_top, width, items, style=BODY_S, gap=3):
        y = y_top
        for t in items:
            p = Paragraph(t, style)
            w, h = p.wrap(width - 12, 1000)
            self.c.setFillColor(GOLD)
            self.c.circle(x + 2.5, y - style.fontSize * 0.62, 1.3, stroke=0, fill=1)
            p.drawOn(self.c, x + 12, y - h)
            y -= h + gap
        return y

    def image(self, name, x, y_top, width=None, height=None, caption=None, align="left"):
        """Place an image by its top-left, scaled to width or height; returns the bottom."""
        path = IMG / f"{name}.png"
        im = Image.open(path)
        iw, ih = im.size
        if width and height:
            s = min(width / iw, height / ih)
        elif width:
            s = width / iw
        else:
            s = height / ih
        w, h = iw * s, ih * s
        if align == "center" and width:
            x += (width - w) / 2
        JPG.mkdir(parents=True, exist_ok=True)
        jp = JPG / f"{name}.jpg"
        if not jp.exists() or jp.stat().st_mtime < path.stat().st_mtime:
            im.convert("RGB").save(jp, quality=90)
        self.c.drawImage(str(jp), x, y_top - h, w, h)
        y = y_top - h
        if caption:
            y = self.para(x, y - 5, max(w, 120), caption, CAP)
        return y

    def table(self, x, y_top, cols, rows, widths, head=True, row_h=None, style=BODY_S, swatch=None, lines=True):
        """Simple ruled table. cols: header labels; rows: lists of strings."""
        c = self.c
        y = y_top
        if head:
            xx = x
            for label, w in zip(cols, widths):
                self.spaced(xx + (14 if swatch and xx == x else 0), y - 9, label.upper(), size=6.8, color=GREY,
                            space=1.8)
                xx += w
            y -= 15
            c.setStrokeColor(INK)
            c.setLineWidth(0.6)
            c.line(x, y, x + sum(widths), y)
        for r_i, row in enumerate(rows):
            hs = []
            paras = []
            for t, w in zip(row, widths):
                p = Paragraph(t, style)
                _, h = p.wrap(w - 10, 1000)
                paras.append(p)
                hs.append(h)
            h = max(max(hs), row_h or 0) + 7
            xx = x
            for k, (p, w) in enumerate(zip(paras, widths)):
                off = 0
                if swatch and k == 0:
                    col = swatch[r_i]
                    if col:
                        c.setFillColor(HexColor(col))
                        c.setStrokeColor(HAIR)
                        c.setLineWidth(0.4)
                        c.rect(xx, y - 5 - 7.5, 7.5, 7.5, stroke=1, fill=1)
                    off = 14
                p.drawOn(c, xx + off, y - 4 - p.height if hasattr(p, "height") else y - 4 - hs[k])
                xx += w
            y -= h
            if lines:
                c.setStrokeColor(HAIR)
                c.setLineWidth(0.4)
                c.line(x, y, x + sum(widths), y)
        return y


# ---- the pages ----------------------------------------------------------------------
def cover(c):
    pg = Page(c, None, None)
    pg.mark(W / 2, H - 70, 1.2)
    pg.spaced(W / 2, H - 92, "BATHSHEVA LONDON", size=7.6, space=2.6, align="center")
    im_top = H - 120
    pg.image("00_hero", W / 2 - 150, im_top, width=300)
    c.setFont("Garamond", 54)
    c.setFillColor(INK)
    c.drawCentredString(W / 2, 190, "Faro")
    c.setFont("Garamond-Italic", 15)
    c.setFillColor(GREY)
    c.drawCentredString(W / 2, 166, "Prototype build manual")
    pg.rule(W / 2 - 25, 150, 50)
    pg.spaced(W / 2, 70, "ROSSO  ·  LOOKS-LIKE PROTOTYPE  ·  SEPTEMBER 2026", size=6.8, color=GREY, space=1.9,
              align="center")


def before_you_begin(c):
    pg = Page(c, "Before you begin", 2)
    pg.kicker(H - 110, "Introduction")
    pg.title(H - 145, "Before you begin")
    y = pg.para(L, H - 160, 330, "From the box of printed parts to a finished, glowing prototype ready to "
                "photograph.", STAND)
    pg.rule(L, y - 12)
    y = pg.para(L, y - 26, R - L, "Faro is built from seventeen printed pieces, finished by hand in four colours and "
                "glued together in a set order. Nothing here is difficult, but each stage needs patience: thin coats "
                "of paint, time to dry, and a dry fit before any glue. Each step ends with a checkpoint; don't move on "
                "until it is met.")
    pg.heading(L, y - 22, "Timing")
    y -= 30
    cols = [("Weekend one", "Inspect and dry-fit, prepare the surfaces, prime, and paint the colours."),
            ("The week between", "Let the paint harden. It feels dry within hours but needs days to cure."),
            ("Weekend two", "Clear coat, assemble, light it and photograph.")]
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
    # safety box
    box_top = y
    items = ["Spray outdoors or somewhere very well ventilated, and wear the respirator whenever you spray.",
             "Wear a dust mask or the respirator, and nitrile gloves, when sanding resin: its dust shouldn't be "
             "breathed in or left on skin.",
             "Wear nitrile gloves when mixing or applying epoxy.",
             "Keep sprays and epoxy away from children and pets, and let fumes clear before bringing parts indoors."]
    pg.heading(L + 14, y - 18, "Safety", color=RED)
    yb = pg.bullets(L + 14, y - 28, R - L - 28, items)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.rect(L, yb - 8, R - L, box_top - (yb - 8), stroke=1, fill=0)
    y = yb - 34
    pg.heading(L, y, "How to use this manual")
    pg.para(L, y - 10, 225, "Work through the seven steps in order. Each part's colour and treatment is listed on "
            "the next page; keep it open while you paint. If something goes wrong, turn to Troubleshooting at the "
            "back: almost every mistake can be sanded out and repainted.")
    pg.image("09_view_lantern", L + 250, y + 6, width=R - L - 250, caption="The lantern, finished.")


SW = {"red": "#8A1C15", "cream": "#F6EAD2", "gold": "#C4A15A", "umber": "#4E3222", "black": "#1F1D1C",
      "frost": "#EEEBE3"}


def parts_and_supplies(c):
    pg = Page(c, "Parts and supplies", 3)
    pg.kicker(H - 110, "Inventory")
    pg.title(H - 145, "Parts and supplies")
    rows = [("base", "1", "Sponged wood effect", "umber"), ("base_plate", "1", "Black acrylic, or leave primed", "black"),
            ("nameplate", "1", "Gold, black round the letters", "gold"),
            ("band_cream", "1", "Cream gloss, clear coat", "cream"), ("band_red", "1", "Red gloss, clear coat", "red"),
            ("tower", "1", "Cream gloss, clear coat", "cream"), ("knob", "1", "Gold; decorative, it doesn't turn", "gold"),
            ("gallery", "1", "Gold, light coats only", "gold"), ("lantern_frame", "1", "Gold, light coats only", "gold"),
            ("cap", "1", "Red gloss, clear coat", "red"), ("finial", "1", "Gold", "gold"),
            ("lantern_glass", "1", "Leave unpainted", "frost"),
            ("window_diffuser_1 to 5", "5", "Leave unpainted", "frost")]
    y = pg.table(L, H - 172, ["Part", "Qty", "Finish"], [r[:3] for r in rows], [180, 50, R - L - 230],
                 swatch=[SW[r[3]] for r in rows], style=BODY_S)
    pg.heading(L, y - 26, "Supplies")
    left = ["Grey filler primer", "Red gloss spray", "Cream gloss spray (Ivory Bisque)", "Metallic gold spray",
            "Clear lacquer", "Black and burnt umber acrylic, small brush and sponge", "Wet-and-dry paper, P240 to P1200"]
    right = ["Tamiya masking tape, 10 mm", "Araldite Rapid epoxy, cocktail sticks", "Black self-adhesive felt",
             "Warm white copper fairy lights, 3 AA batteries", "Rechargeable warm white LED puck, under 45 mm",
             "A few coins for weight", "Respirator, dust mask, nitrile gloves",
             "Craft knife, blu-tack"]
    y1 = pg.bullets(L, y - 38, (R - L) / 2 - 10, left)
    y2 = pg.bullets(L + (R - L) / 2 + 6, y - 38, (R - L) / 2 - 10, right)


def step1(c):
    pg = Page(c, "Step 1", 4)
    pg.kicker(H - 110, "Step 01")
    pg.title(H - 145, "Inspect and dry-fit")
    y = pg.para(L, H - 160, 340, "Check every part and fit them together without glue. Paint adds thickness, so "
                "tight fits only get tighter.", STAND)
    pg.rule(L, y - 12)
    top = y - 30
    pg.image("02_exploded_resin", L - 16, top + 8, width=240)
    x = L + 232
    yy = pg.steps(x, top, R - x, [
        "Tick off every part against the inventory. Look for cracks, warping or broken railing posts.",
        "Stack without glue: base, cream band, red band, tower, gallery. Each joint should sit flat and centred.",
        "Stand the lantern glass on the gallery and lower the frame over it. It should sit without forcing.",
        "Twist the cap on. Under it are four lugs, small tabs that drop through four slots in the lantern top; "
        "then turn it clockwise to the stop.",
        "Hold each diffuser behind its window: its number and arrow face inwards, arrow up. They are not "
        "interchangeable.",
        "Press the base plate into the rebate: the shallow step cut round the opening under the base.",
        "Stand it where it would live and judge size and proportions."], style=BODY_S, gap=4)
    hw = (R - x - 10) / 2
    y1 = pg.image("11_drystack_resin", x, yy - 12, width=hw, height=150, caption="Dry-stacked: knob and nameplate "
                  "aligned on the front.")
    y2 = pg.image("08_cap_twist_resin", x + hw + 10, yy - 12, width=hw,
                  caption="Lugs over the slots: drop the cap in (1), turn clockwise to the stop (2).")
    pg.checkpoint(min(y1, y2, 190) - 22, "every part is present and undamaged, the stack stands straight, and the "
                  "cap twists on and off without forcing.")


def step2(c):
    pg = Page(c, "Step 2", 5)
    pg.kicker(H - 110, "Step 02")
    pg.title(H - 145, "Prepare the surfaces")
    y = pg.para(L, H - 160, 360, "Clean, smooth surfaces are what make the paint look expensive.", STAND)
    pg.rule(L, y - 12)
    y = pg.steps(L, y - 30, R - L, [
        "Wash all parts in warm soapy water, rinse, and leave to dry fully.",
        "Trim any support nubs with a craft knife, cutting away from yourself.",
        "Put on a dust mask or the respirator, and gloves. Sand visible surfaces with P240 to flatten marks, then "
        "P400 to smooth.",
        "Wipe the dust off with a barely damp cloth and let dry."])
    y = pg.image("01_printed_parts", L + 45, y - 10, width=R - L - 90,
                 caption="Every printed part, as it arrives in plain white resin.")
    box_top = y - 18
    pg.heading(L + 14, box_top - 18, "Handle with care", color=RED)
    yb = pg.bullets(L + 14, box_top - 28, R - L - 28, [
        "<b>Gallery and lantern frame:</b> only remove support marks; the posts are delicate.",
        "<b>Nameplate:</b> sand the flat face only, never across the raised letters.",
        "<b>Lantern glass and diffusers:</b> never sand; they arrive frosted. Keep the small raised number and "
        "arrow on each diffuser. Set them aside, clean."])
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.rect(L, yb - 8, R - L, box_top - (yb - 8), stroke=1, fill=0)
    pg.checkpoint(yb - 30, "every part is clean, dry and dust-free, with no support marks left on the surfaces "
                  "that show.")


def step3(c):
    pg = Page(c, "Step 3", 6)
    pg.kicker(H - 110, "Step 03")
    pg.title(H - 145, "Prime")
    y = pg.para(L, H - 160, 360, "Primer fills fine layer lines and shows every flaw. This is where the final finish "
                "is really made.", STAND)
    pg.rule(L, y - 12)
    y = pg.steps(L, y - 30, R - L, [
        "Mount parts on a tube, bottle or cocktail sticks with blu-tack, so you can reach all round without "
        "touching.",
        "Choose a dry, still day, around 15 to 25°C. Shake the primer for two to three minutes.",
        "Spray light coats from 25 to 30 cm, starting and finishing each pass off the part.",
        "Let it dry, then sand with P400, wearing the dust mask. Repeat until the surfaces look smooth under a "
        "bright light.",
        "Prime every part except the lantern glass and diffusers. On the gallery and frame, one or two mist coats "
        "only."])
    y = pg.para(L, y - 8, R - L, "<b>Drying times.</b> Typically touch-dry in 15 to 30 minutes, ready for the next "
                "coat after about 30 minutes, and ready to sand after at least an hour. Brands vary, so check the "
                "can.", NOTE)
    y = pg.image("03_priming", L, y - 16, width=R - L,
                 caption="Every part mounted for priming, except the glass and diffusers.")
    pg.checkpoint(y - 26, "every part is an even grey, with no layer lines, pits or bare spots under a bright "
                  "light.")


def step4(c):
    pg = Page(c, "Step 4", 7)
    pg.kicker(H - 110, "Step 04")
    pg.title(H - 145, "Paint")
    y = pg.para(L, H - 160, 380, "Every part is a single colour, so no masking between colours is needed. Tape only "
                "the surfaces that will be glued.", STAND)
    pg.rule(L, y - 12)
    rows = [("Red gloss", "band_red, cap"), ("Cream gloss", "band_cream, tower"),
            ("Metallic gold", "gallery, lantern_frame, knob, finial, nameplate"),
            ("Burnt umber", "base, sponged wood effect"), ("Black", "base_plate, and the recesses round the letters")]
    y = pg.table(L, y - 24, ["Colour", "Parts"], rows, [150, R - L - 150],
                 swatch=[SW[k] for k in ("red", "cream", "gold", "umber", "black")])
    y = pg.image("04_paint_groups", L, y - 12, width=R - L)
    col = (R - L) / 2 - 10
    pg.heading(L, y - 20, "Mask before painting")
    ym = pg.bullets(L, y - 32, col, [
        "The band rims: the top and bottom faces of the cream and red bands",
        "The tower's bottom rim",
        "The gallery's underside",
        "The back of the knob",
        "The nameplate recess on the base",
        "The lantern frame's bottom ring"], gap=2)
    ym = pg.para(L, ym - 4, col, "Glue holds to bare plastic far better than to paint. Peel the tape once the last "
                 "coat is touch-dry.", NOTE)
    x2 = L + (R - L) / 2 + 10
    pg.heading(x2, y - 20, "Spraying")
    ys = pg.steps(x2, y - 32, R - x2, [
        "Three or four light coats, 25 to 30 cm away.",
        "On the tower, spray at an angle into each window so the edges are covered.",
        "On the gallery and frame, use short bursts from several directions.",
        "If dust or a run appears, let it dry, sand with P1200 and respray lightly.",
        "For richer brass, spray gloss black first and gold over it."], style=BODY_S, gap=2, num_w=20)
    ys = pg.para(x2, ys - 4, R - x2, "<b>Drying times.</b> Typically touch-dry in 15 to 30 minutes, with the next "
                 "coat after 15 to 30 minutes. Some enamel sprays must be recoated within an hour or not until 48 "
                 "hours later, so check the can.", NOTE)
    pg.para(L, min(ym, ys) - 16, R - L, "The wood effect and the lettering are overleaf; this step's checkpoint "
            "comes after them.", CAP)


def step4b(c):
    pg = Page(c, "Step 4, continued", 8)
    pg.kicker(H - 110, "Step 04, continued")
    pg.title(H - 145, "Wood and lettering")
    pg.rule(L, H - 160)
    pg.heading(L, H - 186, "Walnut base")
    y = pg.steps(L, H - 198, R - L, [
        "Brush a thin coat of burnt umber over the primed base and let it dry.",
        "Dab a barely loaded sponge on kitchen paper, then drag it round the base in one direction. The streaks "
        "read as grain.",
        "Build two or three passes until it reads as dark walnut. Unevenness looks natural."], style=BODY_S, gap=3)
    pg.heading(L, y - 22, "Nameplate letters")
    y = pg.para(L, y - 34, R - L, "Once the gold is dry, brush thinned black acrylic over the letters, then wipe the "
                "raised surfaces with a damp cloth before it dries. The black stays round the letters and makes FARO "
                "easy to read.", BODY_S)
    cw = (R - L) / 2
    pg.image("12_nameplate_brushed", L, y - 12, width=cw - 10, caption="Brush black over the letters.")
    y = pg.image("12_nameplate_wiped", L + cw + 10, y - 12, width=cw - 10,
                 caption="Wipe the raised surface: FARO stands out in gold.")
    pg.heading(L, y - 22, "Colour reference")
    cw = (R - L) / 4
    low = y
    for k, (nm, cap) in enumerate((("09_view_front", "Front"), ("09_view_side", "Side"), ("09_view_rear", "Rear"),
                                   ("09_view_three_quarter", "Three-quarter"))):
        low = min(low, pg.image(nm, L + k * cw, y - 30, width=cw - 8, caption=cap))
    pg.checkpoint(low - 22, "every part is evenly coloured with no bare patches or runs, the base reads as dark "
                  "walnut, FARO stands out in gold, and the masking tape is off.")


def step5_6(c):
    pg = Page(c, "Steps 5 and 6", 9)
    pg.kicker(H - 110, "Step 05")
    pg.title(H - 145, "Clear coat and cure")
    pg.rule(L, H - 160)
    y = pg.steps(L, H - 176, R - L, [
        "Wait at least 24 hours after the last colour coat.",
        "Test first. Spray a little clear lacquer on a hidden inside surface, such as the inside of the cap rim, "
        "and leave it an hour. Some paints wrinkle or cloud under some clears; if it stays smooth, carry on.",
        "Spray two light coats of clear lacquer on the red and cream parts only: band_red, cap, band_cream and "
        "tower.",
        "Leave the gold and the wood-effect base uncoated; clear can dull metallic paint.",
        "Leave everything warm, dry and dust-free for two to three days. Paint feels dry long before it is hard.",
        "Optional: once hard, polish the red and cream parts with car polishing compound."], style=BODY_S, gap=3)
    y = pg.para(L, y - 6, R - L, "<b>Drying times.</b> Clear lacquer is typically touch-dry in about 30 minutes, "
                "with the second coat after 15 to 30 minutes. Check the can.", NOTE)
    y = pg.checkpoint(y - 16, "the gloss is even and hard: a fingernail pressed on a hidden spot leaves no mark.")
    pg.kicker(y - 34, "Step 06")
    pg.title(y - 68, "Assemble")
    y = pg.para(L, y - 82, 400, "Araldite Rapid gives about five minutes to position a joint. Mix small amounts, one "
                "joint at a time, and hold or tape each joint as it sets.", STAND)
    pg.rule(L, y - 10)
    y = pg.bullets(L, y - 26, R - L, [
        "Wait about 20 to 30 minutes before handling a glued joint or starting the next one.",
        "Epoxy reaches full strength the next day: leave the finished lamp overnight before lifting it by the "
        "top or testing the cap hard.",
        "Dry-fit each joint just before you glue it, and wipe off any squeeze-out with a cocktail stick before "
        "it sets."], style=BODY_S)
    pg.heading(L, y - 22, "The diffusers")
    y = pg.para(L, y - 34, R - L, "Each diffuser carries its number and an up arrow, raised on its inner face on a "
                "small tab below the window. The tab sits behind the tower wall, so the marks never show. Fit each "
                "one with the arrow pointing up and the smooth, curved outer face against the window. Glue them "
                "first, while the tower is still open at both ends: 1, 2 and 3 from the bottom, 4 and 5 from the "
                "top.", BODY_S)
    pg.image("05_diffuser_marks", L, y - 12, width=R - L,
             caption="The five diffusers from inside the tower (left), and one from above (right): the curved "
                     "outer face goes against the window.")


def diffuser_map(c):
    pg = Page(c, "Step 6, continued", 10)
    pg.kicker(H - 110, "Step 06, continued")
    pg.title(H - 145, "Which window is which")
    pg.rule(L, H - 160)
    y = H - 186
    pg.heading(L, y, "Diffuser map, seen from above")
    import math
    cx, cy, r = L + 95, y - 105, 68
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    c.circle(cx, cy, r, stroke=1, fill=0)
    c.setStrokeColor(HAIR)
    c.circle(cx, cy, r - 12, stroke=1, fill=0)
    for lab, ang, sub in (("1 · 5", 0, "front"), ("2", 90, "right"), ("3", 180, "rear"), ("4", 270, "left")):
        a = math.radians(ang)
        x, yy = cx + r * math.sin(a), cy - r * math.cos(a)
        rr = 9 if len(lab) > 1 else 7
        c.setFillColor(HexColor("#F3E3C4"))
        c.setStrokeColor(RED)
        c.setLineWidth(0.6)
        c.circle(x, yy, rr, stroke=1, fill=1)
        c.setFillColor(RED)
        c.setFont("Garamond", 8.5 if len(lab) > 1 else 9)
        c.drawCentredString(x, yy - 3, lab)
        c.setFillColor(GREY)
        c.setFont("Garamond-Italic", 9)
        dx, dy = 22 * math.sin(a), -20 * math.cos(a)
        c.drawCentredString(x + dx, yy + dy - 3, sub)
    rows = [("1", "Front, lowest", "113 mm", "Bottom"), ("2", "Right side (seen from the front)", "126 mm", "Bottom"),
            ("3", "Rear", "139 mm", "Bottom"), ("4", "Left side", "152 mm", "Top"), ("5", "Front, highest", "165 mm", "Top")]
    pg.table(L + 225, y - 12, ["No.", "Window", "Height", "Glue from"], rows, [36, R - L - 225 - 146, 55, 55])
    pg.image("05_diffuser_map", L + 60, cy - 100, width=R - L - 120,
             caption="The numbered windows, lit. Hold each diffuser to its window before gluing.")


ASSEMBLY = [
    ("Diffusers into the tower", "With the tower still open at both ends, glue each diffuser behind its window: "
     "arrow up, curved face against the window. Reach 1, 2 and 3 from the bottom and 4 and 5 from the top. Use tiny "
     "dabs at the edges only.", ["06_01_diffusers"]),
    ("Nameplate", "Into its recess on the front of the base.", ["06_02_nameplate"]),
    ("Knob", "Onto the front of the red band, centred. On the prototype it is decorative and doesn't turn.",
     ["06_03_knob"]),
    ("Thread the lights", "In through the USB-C port at the back of the base and up through the hole in its top. "
     "The battery box stays outside, behind the lamp.", ["06_04_fairy_lights"]),
    ("Stack and glue", "The cream band onto the base, then the red band, then the tower, with knob and nameplate "
     "aligned. Pull the lights up as you go, and let each joint set before the next.", ["06_05_stack"]),
    ("Coil the lights", "Loosely inside the tower so some sit near each window. Hold each coil in place with a "
     "small dab of blu-tack or tape near its window. Keep them all in the tower.", ["06_06_coil_lights"]),
    ("Glow test", "Before the gallery goes on, switch the lights on and check all five windows glow evenly. If one "
     "is dark or patchy, move its coil through the open top, fix it again, and test once more.",
     ["06_07_glow_test"]),
    ("Gallery", "Onto the tower top, centred.", ["06_08_gallery"]),
    ("Lantern", "Stand the empty glass on the gallery, lower the frame over it and glue the frame to the gallery. "
     "The lantern stays empty for the brightness test.", ["06_09_lantern"]),
    ("Finial and cap", "Glue the finial into the cap. Then twist the cap on: lugs over the slots, drop it in (1) and "
     "turn clockwise to the stop (2). Do not glue it.", ["06_10_finial", "06_10_twist_cap"]),
    ("Weight", "Tape a few coins low inside the base, clear of the wire.", ["06_11_weight"]),
    ("Underneath", "Glue the base plate into the rebate under the base, then stick on the felt, trimmed to size.",
     ["06_12_underneath"]),
]
IMG_W, IMG_H = 200, 118


def assembly_rows(pg, y, rows, first):
    c = pg.c
    for k, (title, text, imgs) in enumerate(rows):
        n = first + k
        share = [1.0] if len(imgs) == 1 else [0.38, 0.62]      # images on the left (the cap twist gets more room)...
        low, xi = y, L
        for nm, f in zip(imgs, share):
            wi = (IMG_W - 6 * (len(imgs) - 1)) * f
            low = min(low, pg.image(nm, xi, y, width=wi, height=IMG_H if len(imgs) == 1 else IMG_H + 20,
                                    align="center"))
            xi += wi + 6
        x = L + IMG_W + 22                                    # ...the step on the right
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


def assembly_pages(c, number):
    """Step 6 in three pages of four, each step beside its picture."""
    chunks = [ASSEMBLY[0:4], ASSEMBLY[4:8], ASSEMBLY[8:12]]
    first = 1
    for i, rows in enumerate(chunks):
        pg = Page(c, "Step 6, assembly", number + i)
        pg.kicker(H - 110, f"Step 06, assembly, {i + 1} of 3")
        pg.title(H - 145, "Assembly order" if i == 0 else "Assembly, continued", size=26)
        pg.rule(L, H - 158)
        y = assembly_rows(pg, H - 176, rows, first)
        first += len(rows)
        if i == len(chunks) - 1:
            pg.checkpoint(y - 4, "the glue has set overnight, all five windows glow evenly, the cap twists on "
                          "and off, and the lamp stands level on its felt.")
        c.showPage()


def step7(c, number):
    pg = Page(c, "Step 7", number)
    pg.kicker(H - 110, "Step 07")
    pg.title(H - 145, "Light it and photograph")
    y = pg.para(L, H - 160, 300, "The fairy lights make the windows glow, with about the light of a couple of "
                "candles. The real lamp's light would come from an LED in the lantern, so test that too.", STAND)
    pg.rule(L, y - 12)
    colw = 270
    pg.heading(L, y - 34, "Testing real brightness")
    yy = pg.steps(L, y - 46, colw, [
        "Twist off the cap. The opening is 49 mm across.",
        "Drop a warm white LED puck, under 45 mm across, into the empty lantern glass. Or run a USB LED module's "
        "cable in through the USB-C port and up to a power bank.",
        "Twist the cap back on and switch off the room lights.",
        "Judge it, and note what you see for the lighting ODM."], style=BODY_S, gap=3)
    pg.heading(L, yy - 18, "What good looks like")
    yy = pg.bullets(L, yy - 30, colw, [
        "It softly lights the nearby wall and surface, like a mood lamp.",
        "The frosted glass is bright without glaring.",
        "The light feels warm and domestic, not like a task light."])
    pg.heading(L, yy - 18, "Photographs")
    yy = pg.bullets(L, yy - 30, colw, [
        "Two sets: soft daylight with the lamp off; dusk with the lamp on.",
        "A plain backdrop, plus one styled shelf scene with books and a plant.",
        "Front, side, three-quarter, rear, lantern close-up, nameplate.",
        "Hide the battery box, power bank and cables out of shot."])
    x2 = L + colw + 24
    y2 = pg.image("07_cutaway", x2, y - 20, width=R - x2,
                  caption="Inside: the lights coiled in the tower, the puck in the empty lantern, coins in the base.")
    yi = pg.image("10_puck_insert", L, yy - 14, width=130, caption="The puck rests on the ledge inside the gallery.")
    pg.image("00_hero", L + 150, yy - 14, width=80, caption="The goal: a soft, warm glow.")
    pg.checkpoint(min(yi, y2) - 20, "the windows and lantern glow softly, the test record is filled in, and both "
                  "photo sets are taken.")


def troubleshooting(c, number):
    pg = Page(c, "Troubleshooting", number)
    pg.kicker(H - 110, "Reference")
    pg.title(H - 145, "Troubleshooting")
    y = pg.para(L, H - 160, 380, "Almost every problem is recoverable. Let paint harden fully before sanding or "
                "recoating.", STAND)
    pg.rule(L, y - 12)
    rows = [("Cap won't twist on, or sticks", "Sand the lugs (the small tabs under the cap) and the underside of the "
             "slots lightly with P400, and test before adding more paint."),
            ("Paint run or sag", "Let it harden, sand flat with P1200 and spray a light coat over it."),
            ("Rough, bumpy gloss (orange peel)", "Sand gently with P1200 and polish, or add another light clear coat. "
             "Next time, lighter coats."),
            ("Dust specks", "Once hard, sand the speck with P1200 and respray lightly on a still day."),
            ("Clear coat wrinkles or clouds", "Let it harden, sand back and respray the colour. Next time, test the "
             "clear on a hidden surface first."),
            ("Paint clogged in the railing", "Clear the gaps with a cocktail stick while still wet. Once dry, don't "
             "force the posts."),
            ("Bright LED dots in a window", "Stick a small piece of baking paper behind that diffuser, or move the "
             "lights slightly away."),
            ("A window is dark or patchy", "At the glow test, before the gallery goes on: move a coil closer to that "
             "window through the open top and fix it with blu-tack or tape. Later, nudge it with a long cocktail "
             "stick through the cap opening and the hole in the gallery."),
            ("A diffuser is upside down or swapped", "Before the glue sets, lift it out and check its number and "
             "arrow. Once set, work it free from inside with a craft knife."),
            ("Lantern too dim, or glaring", "Try a brighter or dimmer puck, or move it lower in the glass. Note the "
             "change for the ODM."),
            ("Lamp wobbles", "Check the felt is flat and fully stuck, and add more coins low in the base.")]
    y = pg.table(L, y - 30, ["Problem", "Fix"], rows, [175, R - L - 175], style=BODY_S)
    pg.image("13_underside", L + 70, y - 14, width=R - L - 140,
             caption="The finished underside: the felt stuck on (left), and peeled back to show the base plate glued "
                     "into its rebate (right).")


def record(c, number):
    pg = Page(c, "Record", number)
    pg.kicker(H - 110, "Reference")
    pg.title(H - 145, "Test record")
    y = pg.para(L, H - 160, 380, "Write down what you learn before changing anything. It becomes the brief for the "
                "production lighting partner.", STAND)
    pg.rule(L, y - 12)
    y -= 36
    for lab in ("LED used", "Power source", "Distance to wall"):
        c.setFont("Garamond", 10.5)
        c.setFillColor(INK)
        c.drawString(L, y, lab)
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.5)
        c.line(L + 120, y - 2, R, y - 2)
        y -= 24
    y -= 8
    scales = [("Brightness", "Too dim", "About right", "Too bright"), ("Warmth", "Too cool", "About right", "Too warm"),
              ("Glare", "None", "Mild", "Distracting"), ("Diffusion", "Even", "Some hot spots", "Hot spots"),
              ("Wall glow", "Weak", "Soft mood light", "Strong")]
    for row in scales:
        c.setFont("Garamond", 10.5)
        c.setFillColor(INK)
        c.drawString(L, y, row[0])
        for k, opt in enumerate(row[1:]):
            x = L + 120 + k * 120
            c.setStrokeColor(GOLD)
            c.setLineWidth(0.6)
            c.circle(x + 4, y + 3.5, 4, stroke=1, fill=0)
            c.setFillColor(INK)
            c.drawString(x + 14, y, opt)
        y -= 24
    pg.heading(L, y - 14, "Notes for the lighting ODM")
    y -= 26
    for k in range(6):
        c.setStrokeColor(HAIR)
        c.line(L, y - k * 22, R, y - k * 22)
    y -= 6 * 22 + 20
    pg.heading(L, y, "Before you finish")
    y -= 18
    for t in ("Cap still twists off", "All five windows glow", "Lantern glass empty when not testing",
              "Battery box and cables hidden in photos", "Changes noted for prototype two"):
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.6)
        c.rect(L, y - 1, 8, 8, stroke=1, fill=0)
        c.setFont("Garamond", 10.5)
        c.setFillColor(INK)
        c.drawString(L + 16, y, t)
        y -= 20


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=A4)
    c.setTitle("Faro, prototype build manual")
    c.setAuthor("Bathsheva London")
    c.setSubject("Rosso, looks-like prototype")
    for fn in (cover, before_you_begin, parts_and_supplies, step1, step2, step3, step4, step4b, step5_6,
               diffuser_map):
        fn(c)
        c.showPage()
    assembly_pages(c, 11)                               # three pages; each ends its own
    for fn in (lambda c: step7(c, 14), lambda c: troubleshooting(c, 15), lambda c: record(c, 16)):
        fn(c)
        c.showPage()
    c.save()
    print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
