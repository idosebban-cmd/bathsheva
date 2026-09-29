"""
Shared ReportLab page furniture for the Bathsheva London prototype build
manuals (currently Faro and Atelier). Both faro/manual/build_manual.py and
atelier/build-manual/build_manual.py import this, so the page layout, type
styles and colours stay identical between manuals rather than drifting as
two separately maintained copies.

Extracted from faro/manual/build_manual.py, which was the first of the two
manuals built; its own Page class now wraps `Page` here with Faro's footer
text and image directories, and its content-drawing functions (cover,
before_you_begin, step1, ...) are unchanged.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

W, H = A4
L, R = 64, W - 64                       # text block
PAPER = HexColor("#F8F4EC")
INK = HexColor("#2B2420")
GREY = HexColor("#6E5F52")
RED = HexColor("#8A1C15")
GOLD = HexColor("#B08A3E")
HAIR = HexColor("#D8CDBC")

# The footer rule sits at y=52 and the footer text at y=38 (see Page.footer);
# body content must not cross below FOOTER_SAFE_Y, or it prints through the
# footer. The header rule sits at H-60, with the kicker/title starting well
# below that already, so only the bottom edge needs a runtime guard.
FOOTER_SAFE_Y = 58


class PageOverflow(Exception):
    """Raised when a page's content would cross the footer rule -- fails the
    build instead of silently printing text or an image under the footer."""


_registered_font_dirs: set[str] = set()


def register_fonts(fonts_dir: Path):
    """Registers the shared Garamond family from `fonts_dir` (a manual's own
    fonts/ folder, e.g. faro/manual/fonts or atelier/build-manual/fonts --
    both currently carry identical copies of the same EB Garamond files).
    Safe to call more than once per process; registers each directory once."""
    key = str(fonts_dir)
    if key in _registered_font_dirs:
        return
    pdfmetrics.registerFont(TTFont("Garamond", str(fonts_dir / "EBGaramond-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Garamond-Italic", str(fonts_dir / "EBGaramond-Italic.ttf")))
    pdfmetrics.registerFont(TTFont("Garamond-Medium", str(fonts_dir / "EBGaramond-Medium.ttf")))
    pdfmetrics.registerFontFamily("Garamond", normal="Garamond", italic="Garamond-Italic", bold="Garamond-Medium")
    _registered_font_dirs.add(key)


BODY = ParagraphStyle("body", fontName="Garamond", fontSize=10.8, leading=15, textColor=INK, alignment=TA_LEFT)
BODY_S = ParagraphStyle("bodys", parent=BODY, fontSize=9.8, leading=13.4)
STAND = ParagraphStyle("stand", fontName="Garamond-Italic", fontSize=14.5, leading=19.5, textColor=GREY)
CAP = ParagraphStyle("cap", fontName="Garamond-Italic", fontSize=9, leading=11.5, textColor=GREY)
CHECK = ParagraphStyle("check", fontName="Garamond-Italic", fontSize=10.6, leading=14.2, textColor=INK)
NOTE = ParagraphStyle("note", fontName="Garamond", fontSize=9.4, leading=12.6, textColor=GREY)


# ---- drawing helpers ------------------------------------------------------------
class Page:
    """One A4 page: paper fill, header (running section title) and footer
    (italic manual name + page number), plus drawing helpers for the body.

    `footer_text` and `img_dir` are the one thing that differs between
    manuals (which manual's name prints in the footer, and where its
    rendered images live) -- everything else here is shared verbatim.
    """

    def __init__(self, c, section, number, *, footer_text, img_dir):
        self.c = c
        self.footer_text = footer_text
        self.img_dir = img_dir
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
        c.drawString(L, 38, self.footer_text)
        c.drawRightString(R, 38, str(n))

    def check_bounds(self, y, label=""):
        """Raise PageOverflow if `y` (the lowest point your page's content
        reached) crosses the footer rule. Call this with the return value of
        your last drawing call, before c.showPage() -- a layout bug then
        fails the build instead of silently printing under the footer."""
        if y < FOOTER_SAFE_Y:
            raise PageOverflow(f"{label or 'page'}: content bottom at y={y:.1f}pt crosses the footer rule "
                                f"(must stay at or above y={FOOTER_SAFE_Y}pt) -- overflow of "
                                f"{FOOTER_SAFE_Y - y:.1f}pt")

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
        path = self.img_dir / f"{name}.png"
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
        # Drawn straight from the PNG, not a re-encoded JPEG: JPEG's DCT
        # quantization shifts a flat background colour by a level or two
        # even at quality=100, which reads as a faint but real rectangle
        # against the page's own solid paper-colour fill once printed.
        self.c.drawImage(str(path), x, y_top - h, w, h)
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
