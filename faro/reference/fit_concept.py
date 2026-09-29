"""
Measure the Faro concept (faro_concept.png, the straight FRONT view in the
"VIEWS" panel, top right, which has the least perspective).

    python faro/reference/fit_concept.py

Landmarks are pixel positions in the full 2000 x 2000 image, read off a zoomed,
gridded crop. The script converts them to mm at OVERALL_HEIGHT (ground to the
top of the finial) and prints the values used in faro/params.py.
"""
from pathlib import Path

IMG = Path(__file__).parent / "faro_concept.png"
CROP = (1140, 100, 1400, 700)     # front-view panel (x0, y0, x1, y1)

X_AXIS = 1270.0      # centre line (finial ball and tower centres)
Y_TOP = 114.0        # top of the finial ball
Y_GROUND = 678.0     # bottom of the walnut base

# (y_top, y_bottom, width_px); widths are full diameters in pixels
LANDMARKS = dict(
    base=(618.3, 678.0, 213.0),           # includes a sliver of its top face (camera slightly above)
    cream_band=(606.7, 618.3, 183.0),
    red_band=(548.3, 606.7, 179.0),       # width at its bottom edge
    tower_bottom=(548.3, 548.3, 162.0),
    tower_top=(308.3, 308.3, 123.0),
    gallery_platform=(290.0, 308.3, 169.0),
    railing=(263.3, 290.0, 165.0),
    lantern=(211.7, 290.0, 104.0),        # glazing, partly behind the railing
    cap_rim=(200.0, 211.7, 134.0),
    cap_dome=(150.0, 200.0, 110.0),
    finial_neck=(139.0, 150.0, 18.0),
    finial_ball=(114.0, 139.0, 27.0),
    window_upper=(347.3, 387.3, 22.3),
    window_lower=(446.7, 485.0, 21.0),
    knob=(560.0, 598.3, 38.0),
    nameplate=(636.7, 658.3, 70.0),
)


def fit(overall_height=300.0):
    s = overall_height / (Y_GROUND - Y_TOP)
    z = lambda y: (Y_GROUND - y) * s
    out = {"mm_per_px": s}
    for k, (yt, yb, w) in LANDMARKS.items():
        out[k] = dict(z_bottom=round(z(yb), 1), z_top=round(z(yt), 1), dia=round(w * s, 1))
    return out


if __name__ == "__main__":
    for k, v in fit().items():
        print(k, v)
