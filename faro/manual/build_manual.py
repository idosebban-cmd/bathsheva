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
                "of paint, time to dry, and a dry fit before any glue.")
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
             "Wear nitrile gloves when sanding resin and when mixing or applying epoxy.",
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
            ("tower", "1", "Cream gloss, clear coat", "cream"), ("knob", "1", "Gold", "gold"),
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
             "A few coins for weight", "Respirator, nitrile gloves, craft knife, blu-tack"]
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
    pg.image("02_exploded_resin", L - 16, top + 8, height=top - 70)
    x = L + 232
    yy = pg.steps(x, top, R - x, [
        "Tick off every part against the inventory. Look for cracks, warping or broken railing posts.",
        "Stack without glue: base, cream band, red band, tower, gallery. Each joint should sit flat and centred.",
        "Stand the lantern glass on the gallery and lower the frame over it. It should sit without forcing.",
        "Twist the cap on: lugs down through the slots, then clockwise to the stop.",
        "Hold each numbered diffuser behind its window. They are not interchangeable.",
        "Press the base plate into the rebate under the base.",
        "Stand it where it would live and judge size and proportions."], style=BODY_S, gap=4)
    yy = pg.image("11_drystack_resin", x, yy - 14, width=R - x,
                  caption="Dry-stacked: knob and nameplate aligned on the front.")
    pg.image("08_cap_twist_resin", x, yy - 14, width=R - x, caption="The cap drops in and turns clockwise to lock.")


def step2(c):
    pg = Page(c, "Step 2", 5)
    pg.kicker(H - 110, "Step 02")
    pg.title(H - 145, "Prepare the surfaces")
    y = pg.para(L, H - 160, 360, "Clean, smooth surfaces are what make the paint look expensive.", STAND)
    pg.rule(L, y - 12)
    y = pg.steps(L, y - 30, R - L, [
        "Wash all parts in warm soapy water, rinse, and leave to dry fully.",
        "Trim any support nubs with a craft knife, cutting away from yourself.",
        "Sand visible surfaces with P240 to flatten marks, then P400 to smooth.",
        "Wipe the dust off with a barely damp cloth and let dry."])
    y = pg.image("01_printed_parts", L, y - 16, width=R - L,
                 caption="Every printed part, as it arrives in plain white resin.")
    box_top = y - 22
    pg.heading(L + 14, box_top - 18, "Handle with care", color=RED)
    yb = pg.bullets(L + 14, box_top - 28, R - L - 28, [
        "<b>Gallery and lantern frame:</b> only remove support marks; the posts are delicate.",
        "<b>Nameplate:</b> sand the flat face only, never across the raised letters.",
        "<b>Lantern glass and diffusers:</b> never sand; they arrive frosted. Set them aside, clean."])
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.rect(L, yb - 8, R - L, box_top - (yb - 8), stroke=1, fill=0)


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
        "Let it dry, then sand with P400. Repeat until the surfaces look smooth under a bright light.",
        "Prime every part except the lantern glass and diffusers. On the gallery and frame, one or two mist coats "
        "only."])
    pg.image("03_priming", L, y - 18, width=R - L,
             caption="Every part mounted for priming, except the glass and diffusers.")


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
    pg.heading(L, y - 20, "Spraying")
    y = pg.steps(L, y - 30, R - L, [
        "Three or four light coats, 25 to 30 cm away, waiting between coats as the can directs.",
        "On the tower, spray at an angle into each window so the edges are covered.",
        "On the gallery and frame, use short bursts from several directions.",
        "If dust or a run appears, let it dry, sand with P1200 and respray lightly.",
        "For richer brass, spray gloss black first and gold over it."], style=BODY_S, gap=2)
    pg.heading(L, y - 18, "Colour reference")
    cw = (R - L) / 4
    for k, (nm, cap) in enumerate((("09_view_front", "Front"), ("09_view_side", "Side"), ("09_view_rear", "Rear"),
                                   ("09_view_three_quarter", "Three-quarter"))):
        pg.image(nm, L + k * cw, y - 26, width=cw - 8, caption=cap)


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
        "Build two or three passes until it reads as dark walnut. Unevenness looks natural."])
    pg.heading(L, y - 34, "Nameplate letters")
    y = pg.para(L, y - 46, R - L, "Once the gold is dry, brush thinned black acrylic over the letters, then wipe the "
                "raised surfaces with a damp cloth before it dries. The black stays round the letters and makes FARO "
                "easy to read.")
    cw = (R - L) / 2
    pg.image("12_nameplate_brushed", L, y - 18, width=cw - 10, caption="Brush black over the letters.")
    pg.image("12_nameplate_wiped", L + cw + 10, y - 18, width=cw - 10,
             caption="Wipe the raised surface: FARO stands out in gold.")


def step5_6(c):
    pg = Page(c, "Steps 5 and 6", 9)
    pg.kicker(H - 110, "Step 05")
    pg.title(H - 145, "Clear coat and cure")
    pg.rule(L, H - 160)
    y = pg.steps(L, H - 176, 360, [
        "Wait at least 24 hours after the last colour coat.",
        "Spray two light coats of clear lacquer on the red and cream parts only: band_red, cap, band_cream and "
        "tower.",
        "Leave the gold and the wood-effect base uncoated; clear can dull metallic paint.",
        "Leave everything warm, dry and dust-free for two to three days. Paint feels dry long before it is hard.",
        "Optional: once hard, polish the red and cream parts with car polishing compound."], style=BODY_S, gap=3)
    pg.kicker(y - 22, "Step 06")
    pg.title(y - 56, "Assemble")
    y = pg.para(L, y - 70, 380, "Araldite Rapid sets in about five minutes. Mix small amounts, one joint at a time, "
                "and hold or tape each joint as it sets.", STAND)
    pg.rule(L, y - 10)
    y -= 30
    pg.heading(L, y, "Diffuser map, seen from above")
    # top-view diagram
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
    rows = [("1", "Front, lowest", "113 mm"), ("2", "Right side (seen from the front)", "126 mm"), ("3", "Rear", "139 mm"),
            ("4", "Left side", "152 mm"), ("5", "Front, highest", "165 mm")]
    pg.table(L + 225, y - 12, ["No.", "Window", "Height"], rows, [45, R - L - 225 - 110, 65])
    pg.image("05_diffuser_map", L + 225, cy - 70, width=R - L - 225,
             caption="Each diffuser is numbered; hold it to its window first.")


def assembly_order(c):
    pg = Page(c, "Step 6, continued", 10)
    pg.kicker(H - 110, "Step 06, continued")
    pg.title(H - 145, "Assembly order")
    pg.rule(L, H - 160)
    y = pg.steps(L, H - 176, R - L, [
        "<b>Diffusers into the tower.</b> Through the open top, glue each behind its window with tiny dabs at the "
        "edges only.",
        "<b>Nameplate</b> into its recess on the front of the base.",
        "<b>Knob</b> onto the front of the red band, centred.",
        "<b>Thread the lights</b> in through the USB-C port at the back of the base and up through the hole in its "
        "top. The battery box stays outside, behind the lamp.",
        "<b>Stack and glue</b> the cream band onto the base, then the red band, then the tower, with knob and "
        "nameplate aligned. Pull the lights up as you go.",
        "<b>Coil the lights</b> loosely inside the tower so some sit near each window. Keep them all in the tower.",
        "<b>Gallery</b> onto the tower top.",
        "<b>Lantern.</b> Stand the empty glass on the gallery, lower the frame over it and glue the frame to the "
        "gallery. The lantern stays empty for the brightness test.",
        "<b>Finial</b> into the cap, then twist the cap on, clockwise to the stop. Do not glue it.",
        "<b>Weight.</b> Tape a few coins low inside the base.",
        "<b>Underneath.</b> Glue the base plate into its rebate, then apply the felt, trimmed to size."],
        style=BODY_S, gap=4)
    pg.heading(L, y - 24, "Underneath: felt on, and lifted")
    pg.image("13_underside", L, y - 34, width=R - L,
             caption="The finished underside. In the prototype the plate is glued and the felt simply stuck on.")


GRID = [("06_p1_1_diffusers", "1  Diffusers in"), ("06_p1_2_nameplate", "2  Nameplate"), ("06_p1_3_knob", "3  Knob"),
        ("06_p1_4_fairy_lights", "4  Thread the lights"), ("06_p1_5_band_cream", "5  Cream band"),
        ("06_p1_6_band_red", "5  Red band"), ("06_p1_7_tower", "5  Tower"), ("06_p1_8_coil_lights", "6  Coil the lights"),
        ("06_p2_1_gallery", "7  Gallery"),
        ("06_p2_2_glass", "8  Lantern glass"), ("06_p2_3_frame", "8  Lantern frame"), ("06_p2_4_finial", "9  Finial"),
        ("06_p2_5_twist_cap", "9  Cap on, clockwise"), ("06_p2_6_weight", "10  Weight"),
        ("06_p2_7_base_plate", "11  Base plate"), ("06_p2_8_felt", "11  Felt"), ("07_cutaway", "Inside, finished"),
        ("00_hero", "Finished")]


def pictures(c, part, number):
    pg = Page(c, "Step 6, in pictures", number)
    pg.kicker(H - 110, "Step 06, in pictures" + (", continued" if part else ""))
    pg.title(H - 145, "Assembly, step by step")
    pg.rule(L, H - 160)
    cells = GRID[part * 9:(part + 1) * 9]
    cw = (R - L - 20) / 3
    ch = (H - 190 - 70) / 3
    for k, (nm, cap) in enumerate(cells):
        col, row = k % 3, k // 3
        x = L + col * (cw + 10)
        y_top = H - 180 - row * ch
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.4)
        c.rect(x, y_top - ch + 22, cw, ch - 24, stroke=1, fill=0)
        pg.image(nm, x + 4, y_top - 4, width=cw - 8, height=ch - 32, align="center")
        c.setFont("Garamond-Italic", 9.5)
        c.setFillColor(GREY)
        c.drawString(x, y_top - ch + 10, cap)


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
    pg.image("10_puck_insert", L, yy - 14, width=150, caption="The puck rests on the ledge inside the gallery.")
    pg.image("00_hero", L + 170, yy - 14, width=90, caption="The goal: a soft, warm glow.")


def troubleshooting(c, number):
    pg = Page(c, "Troubleshooting", number)
    pg.kicker(H - 110, "Reference")
    pg.title(H - 145, "Troubleshooting")
    y = pg.para(L, H - 160, 380, "Almost every problem is recoverable. Let paint harden fully before sanding or "
                "recoating.", STAND)
    pg.rule(L, y - 12)
    rows = [("Cap won't twist on, or sticks", "Sand the lugs and the underside of the slots lightly with P400, and "
             "test before adding more paint."),
            ("Paint run or sag", "Let it harden, sand flat with P1200 and spray a light coat over it."),
            ("Rough, bumpy gloss (orange peel)", "Sand gently with P1200 and polish, or add another light clear coat. "
             "Next time, lighter coats."),
            ("Dust specks", "Once hard, sand the speck with P1200 and respray lightly on a still day."),
            ("Paint clogged in the railing", "Clear the gaps with a cocktail stick while still wet. Once dry, don't "
             "force the posts."),
            ("Bright LED dots in a window", "Stick a small piece of baking paper behind that diffuser, or move the "
             "lights slightly away."),
            ("A window stays dark", "Move a coil of lights closer to it through the cap opening."),
            ("Lantern too dim, or glaring", "Try a brighter or dimmer puck, or move it lower in the glass. Note the "
             "change for the ODM."),
            ("Lamp wobbles", "Check the felt is flat and fully stuck, and add more coins low in the base.")]
    pg.table(L, y - 30, ["Problem", "Fix"], rows, [175, R - L - 175], style=BODY_S)


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
    pages = [cover, before_you_begin, parts_and_supplies, step1, step2, step3, step4, step4b, step5_6,
             assembly_order, lambda c: pictures(c, 0, 11), lambda c: pictures(c, 1, 12), lambda c: step7(c, 13),
             lambda c: troubleshooting(c, 14), lambda c: record(c, 15)]
    for fn in pages:
        fn(c)
        c.showPage()
    c.save()
    print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
