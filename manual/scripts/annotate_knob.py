"""
Adds schematic turn/press/hold arrows to the knob close-up base drawing.
These arrows are instructional annotations, not derived from geometry --
same single-weight black line style as the rest of the art, but hand-drawn
SVG paths, not mesh silhouette lines.
"""

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "figures" / "final" / "knob_closeup_base.svg"
DST = ROOT / "figures" / "final" / "knob_closeup.svg"

CX, CY, R = 73.3, 54.8, 19.8
STROKE = 0.3


def arc_path(cx, cy, r, a0, a1):
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy - r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1))
    large = 1 if abs(a1 - a0) > 180 else 0
    sweep = 0  # SVG y-down, so clockwise-on-page sweep flag
    return f"M {x0:.2f} {y0:.2f} A {r:.2f} {r:.2f} 0 {large} {sweep} {x1:.2f} {y1:.2f}"


def arrowhead(cx, cy, r, angle_deg, size=3.2):
    # small triangular arrowhead tangent to a circle of radius r at angle_deg
    ax = cx + r * math.cos(math.radians(angle_deg))
    ay = cy - r * math.sin(math.radians(angle_deg))
    tangent = angle_deg - 90  # direction of travel along the arc
    t1 = tangent + 150
    t2 = tangent - 150
    p1x = ax + size * math.cos(math.radians(t1))
    p1y = ay - size * math.sin(math.radians(t1))
    p2x = ax + size * math.cos(math.radians(t2))
    p2y = ay - size * math.sin(math.radians(t2))
    return f'<path d="M {ax:.2f} {ay:.2f} L {p1x:.2f} {p1y:.2f} M {ax:.2f} {ay:.2f} L {p2x:.2f} {p2y:.2f}" stroke="#0A0A0A" stroke-width="{STROKE}" fill="none" stroke-linecap="round"/>'


def straight_arrow(x0, y0, x1, y1, size=3.0):
    angle = math.degrees(math.atan2(-(y1 - y0), x1 - x0))
    t1, t2 = angle + 150, angle - 150
    p1x, p1y = x1 + size * math.cos(math.radians(t1)), y1 - size * math.sin(math.radians(t1))
    p2x, p2y = x1 + size * math.cos(math.radians(t2)), y1 - size * math.sin(math.radians(t2))
    return (
        f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="#0A0A0A" stroke-width="{STROKE}"/>'
        f'<path d="M {x1:.2f} {y1:.2f} L {p1x:.2f} {p1y:.2f} M {x1:.2f} {y1:.2f} L {p2x:.2f} {p2y:.2f}" stroke="#0A0A0A" stroke-width="{STROKE}" fill="none" stroke-linecap="round"/>'
    )


def main():
    svg = SRC.read_text()
    extra = []

    # PRESS: short straight arrow from directly above, down onto the knob's top edge
    px0, py0 = CX, CY - R - 22
    px1, py1 = CX, CY - R - 2
    extra.append(straight_arrow(px0, py0, px1, py1))
    extra.append(f'<text x="{CX+2:.1f}" y="{py0+6.5:.1f}" font-family="Georgia, serif" font-size="5.0" text-anchor="start" fill="#0A0A0A">PRESS</text>')
    extra.append(f'<text x="{CX+2:.1f}" y="{py0+12:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="3.2" text-anchor="start" fill="#555">play / pause</text>')

    # TURN: arc around the LEFT side of the knob, arrowheads both ends, label to the left
    turn_r = R + 5.5
    extra.append(f'<path d="{arc_path(CX, CY, turn_r, 140, 220)}" stroke="#0A0A0A" stroke-width="{STROKE}" fill="none"/>')
    extra.append(arrowhead(CX, CY, turn_r, 140))
    extra.append(arrowhead(CX, CY, turn_r, 220))
    extra.append(f'<text x="{CX-turn_r-18:.1f}" y="{CY-16.5:.1f}" font-family="Georgia, serif" font-size="5.0" text-anchor="start" fill="#0A0A0A">TURN</text>')
    extra.append(f'<text x="{CX-turn_r-18:.1f}" y="{CY-11:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="3.2" text-anchor="start" fill="#555">volume</text>')

    # HOLD: dwell icon (dashed ring + clock hands) to the right of the knob
    hx, hy, hr = CX + R + 12.5, CY, 6.5
    extra.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{hr}" stroke="#0A0A0A" stroke-width="{STROKE}" fill="none" stroke-dasharray="1.6,1.4"/>')
    extra.append(f'<line x1="{hx:.1f}" y1="{hy:.1f}" x2="{hx:.1f}" y2="{hy-hr+1.5:.1f}" stroke="#0A0A0A" stroke-width="{STROKE}"/>')
    extra.append(f'<line x1="{hx:.1f}" y1="{hy:.1f}" x2="{hx+hr-3:.1f}" y2="{hy:.1f}" stroke="#0A0A0A" stroke-width="{STROKE}"/>')
    extra.append(f'<text x="{hx:.1f}" y="{hy+hr+9:.1f}" font-family="Georgia, serif" font-size="5.0" text-anchor="middle" fill="#0A0A0A">HOLD</text>')
    extra.append(f'<text x="{hx:.1f}" y="{hy+hr+14:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="3.0" text-anchor="middle" fill="#555">power / pair /</text>')
    extra.append(f'<text x="{hx:.1f}" y="{hy+hr+18:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="3.0" text-anchor="middle" fill="#555">reset</text>')

    svg = svg.replace("</svg>", "\n".join(extra) + "\n</svg>")
    DST.write_text(svg)
    print("wrote", DST)


if __name__ == "__main__":
    main()
