"""
Measure the ATELIER concept image and derive profile parameters.

    python reference/fit_concept.py

The image is a perspective product photo, so measurements are approximate
(assumes a front, orthographic-ish view; the product is turned very slightly,
so left/right fin measurements are averaged).

Two kinds of measurement:
* automatic: the red body's left/right edges on every row (reliable: nothing
  else in the photo is red), for the part of the body above the fins;
* landmarks read off gridded zoom crops (cone outline, fin outline, fin/body
  junction lines, grille, knob, LED, collar, foot). They're listed below in
  image pixels, so you can re-check or correct them.

Below the fins' top points the body's own silhouette is hidden. There, the
body radius comes from the fin/body junction lines instead (a fin root at
+-60 deg shows at r*sin60 across the image).

Output: reference/concept_fit.json and a summary to paste into params.py.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
IMG = HERE / "atelier_concept.png"
OVERALL_HEIGHT = 280.0

# ---- landmarks (image px: x right, y down) ---------------------------------
Y_TIP = 17.5          # nose tip
Y_GROUND = 813.0      # fin tips touch the ground
Y_JOINT = 146.0       # cone / body joint
Y_BODY_BOTTOM = 740.0 # red body meets the collar
X_AXIS = 212.5        # body centre line (mid-body)
SIN_FIN = math.sin(math.radians(60))   # front fins at +-60 deg
FIN_T = 8.0           # fin thickness estimated from the edge band on the right fin (~3.5 mm wide)
                      # its silhouette sits (T/2)cos60 further out than the fin's mid-plane

# cone half-widths (px) at rows (y): left/right edges read off the zoom crop
CONE_HW = [(146, 71.5), (140, 70.0), (120, 63.5), (100, 55.3), (80, 46.4), (60, 35.7),
           (50, 29.0), (40, 21.9), (30, 13.0), (22, 6.0), (17.5, 0.0)]
# fin/body junction: distance from the axis (px), average of left and right fins
FIN_JUNCTION_D = [(600, 112.8), (650, 100.3), (700, 84.9), (738, 71.3)]
FIN_TOP = (556.0, 123.6)            # (y, d) where the fin's upper edge leaves the body
FIN_OUTER = [(600, 156.0), (650, 174.4), (700, 188.6), (750, 196.0), (800, 199.9)]
FIN_TIP = (812.0, 196.0)
FIN_LOWER = [(800, 153.5), (770, 117.5), (757, 97.5), (740, 71.3)]   # tip -> body
# grille: bezel outer edge top/bottom/left/right; mesh top/bottom
BEZEL = dict(top=239, bottom=466, left=116, right=310)
MESH = dict(top=247.5, bottom=457.5)
KNOB = dict(top=509, bottom=564, left=189, right=241)
LED_Y = 490
COLLAR = dict(top=740, bottom=770, top_w=111, bottom_w=77)
FOOT = dict(top=770, bottom=798, w=50.5)


def red_mask(im):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    mx, mn = im.max(-1), im.min(-1)
    s = (mx - mn) / (mx + 1e-6)
    d = mx - mn + 1e-6
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return ((h < 22) | (h > 335)) & (s > 0.42) & (mx > 0.10)


def main():
    im = np.asarray(Image.open(IMG).convert("RGB")).astype(float) / 255
    red = red_mask(im)
    s = OVERALL_HEIGHT / (Y_GROUND - Y_TIP)            # mm per px
    z = lambda y: (Y_GROUND - y) * s

    # body edges above the fins
    rows = []
    for y in range(int(Y_JOINT) + 4, int(FIN_TOP[0]) - 4):
        xs = np.where(red[y])[0]
        if len(xs) > 50:
            rows.append((y, (xs.max() - xs.min()) / 2))
    rows = np.array(rows)
    body = []
    for y0_ in range(int(rows[0, 0]), int(rows[-1, 0]), 16):     # 16 px bins, averaged
        sel = rows[(rows[:, 0] >= y0_) & (rows[:, 0] < y0_ + 16)]
        if len(sel):
            body.append((z(sel[:, 0].mean()), sel[:, 1].mean() * s))
    # extrapolate the top radius from the top rows (the joint row itself is clipped)
    top = rows[rows[:, 0] < rows[0, 0] + 24]
    k = np.polyfit(top[:, 0], top[:, 1], 1)
    r_top_px = np.polyval(k, Y_JOINT)
    # lower body from fin junction lines
    for y, d in FIN_JUNCTION_D:
        body.append((z(y), d * s / SIN_FIN))
    body.sort()
    R = max(r for _, r in body)
    z0, zt = z(Y_BODY_BOTTOM), z(Y_JOINT)
    bh = zt - z0
    r_bottom = COLLAR["top_w"] / 2 * s                  # body meets the collar flush
    r_top = r_top_px * s
    # rounded belly bottom below the lowest junction reading (hidden in the photo)
    zlow, rlow = body[0]
    # the concept's belly is nearly flat underneath: the fin/body joint is already
    # at ~rlow only ~0.7 mm above the bottom. Round that corner a little so the
    # 2.5 mm wall can still follow it.
    belly = [(z0, r_bottom), (z0 + 0.5, r_bottom + 0.55 * (rlow - r_bottom)),
             (z0 + 1.5, r_bottom + 0.85 * (rlow - r_bottom)), (z0 + 3.5, rlow + 0.8),
             (z0 + 7.0, rlow + 2.6)]
    pts = belly + [p for p in body if p[0] > z0 + 10]
    body_norm = [(round(float((zz - z0) / bh), 4), round(float(rr / R), 4)) for zz, rr in pts]
    body_norm.append((1.0, round(r_top / R, 4)))

    ch = OVERALL_HEIGHT - zt
    cone_base_concept = CONE_HW[0][1] * s
    # keep the cone flush with the body top (earlier brief), fading the extra
    # width out towards the tip so the upper cone keeps the concept's shape
    cone_norm = []
    for y, hw in CONE_HW:
        t = (z(y) - zt) / ch
        r = hw * s + (r_top - cone_base_concept) * (1 - t) ** 2
        cone_norm.append((round(float(max(t, 0.0)), 4), round(float(r / r_top), 4)))
    cone_norm[-1] = (1.0, 0.0)

    bez_d = (BEZEL["bottom"] - BEZEL["top"]) * s
    mesh_d = (MESH["bottom"] - MESH["top"]) * s
    zg = z((BEZEL["top"] + BEZEL["bottom"]) / 2)
    r_at = lambda zz: float(np.interp(zz, [p[0] for p in pts], [p[1] for p in pts]))
    zk = z((KNOB["top"] + KNOB["bottom"]) / 2)
    knob_d = (KNOB["right"] - KNOB["left"]) * s
    u = lambda d: (d * s - FIN_T / 2 * math.cos(math.radians(60))) / SIN_FIN
    fin = dict(
        tip_reach=u(FIN_TIP[1]), top=(z(FIN_TOP[0]), u(FIN_TOP[1])),
        outer=[(round(z(y), 1), round(u(d), 1)) for y, d in FIN_OUTER],
        lower=[(round(z(y), 1), round(u(d), 1)) for y, d in FIN_LOWER],
    )
    # ---- fit the model's fin curves to the measured outline -----------------
    # (same construction as model._build_fins: quadratic Bezier edges)
    def bez(p0, p1, p2, n=200):
        t = np.linspace(0, 1, n)[:, None]
        return (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2)

    embed = 9.0
    z_rt, z_rb = fin["top"][0], z0
    meas_up = np.array([(uu, zz) for zz, uu in fin["outer"]] + [(fin["top"][1], fin["top"][0])])
    meas_lo = np.array([(uu, zz) for zz, uu in fin["lower"]])
    best = None
    for u_tip in np.arange(76, 86, 0.5):
        for bulge in np.arange(0.0, 1.0, 0.025):
            top_p = (r_at(z_rt) - embed, z_rt)
            corner = (u_tip, z_rt)
            mid = ((top_p[0] + u_tip) / 2, z_rt / 2)
            c1 = (mid[0] + bulge * (corner[0] - mid[0]), mid[1] + bulge * (corner[1] - mid[1]))
            up = bez(top_p, c1, (u_tip, 0.0))
            e_up = np.mean([np.min(np.hypot(*(up - m).T)) for m in meas_up])
            if best is None or e_up < best[0]:
                best = (e_up, u_tip, bulge)
    e_up, u_tip, bulge = best
    best2 = None
    for flat in np.arange(4, 8.01, 0.5):          # keep a pointed tip, like the concept
        for und in np.arange(-0.8, 0.8, 0.025):
            tip_in = (u_tip - flat, 0.0)
            bot = (r_at(z_rb + 0.01) - embed, z_rb)
            mid2 = ((tip_in[0] + bot[0]) / 2, (tip_in[1] + bot[1]) / 2)
            corner2 = (tip_in[0], bot[1])
            c2 = (mid2[0] + und * (corner2[0] - mid2[0]), mid2[1] + und * (corner2[1] - mid2[1]))
            lo = bez(tip_in, c2, bot)
            e_lo = np.mean([np.min(np.hypot(*(lo - m).T)) for m in meas_lo])
            if best2 is None or e_lo < best2[0]:
                best2 = (e_lo, flat, und)
    e_lo, flat, und = best2
    fin_fit = dict(FIN_TIP_REACH_FRAC=u_tip / R, FIN_OUTER_BULGE=bulge, FIN_TIP_FLAT=flat,
                   FIN_UNDERCUT=und, FIN_ROOT_TOP_FRAC=(z_rt - z0) / bh, FIN_ROOT_BOTTOM_FRAC=0.0,
                   fit_error_upper_mm=e_up, fit_error_lower_mm=e_lo)

    res = dict(fin_fit=fin_fit, 
        mm_per_px=s, BODY_MAX_DIA=2 * R, z0=z0, BASE_CLEARANCE_FRAC=z0 / OVERALL_HEIGHT,
        body_h=bh, CONE_HEIGHT_FRAC=ch / bh, cone_h=ch,
        BODY_TOP_DIA_FRAC=r_top / R, BODY_BOTTOM_DIA_FRAC=r_bottom / R,
        body_profile=body_norm, cone_profile=cone_norm, cone_base_concept_mm=cone_base_concept,
        GRILLE_Z_FRAC=(zg - z0) / bh, bezel_od=bez_d, grille_d=mesh_d,
        BEZEL_WIDTH=(bez_d - mesh_d) / 2,
        GRILLE_DIA_FRAC=mesh_d / (2 * r_at(zg)),
        knob_d=knob_d, z_knob=zk,
        KNOB_GAP_FRAC=(z(BEZEL["bottom"]) - (zk + knob_d / 2)) / bh,
        z_led=z(LED_Y),
        collar_h=(COLLAR["bottom"] - COLLAR["top"]) * s, collar_top_d=COLLAR["top_w"] * s,
        collar_bottom_d=COLLAR["bottom_w"] * s,
        foot_h=(FOOT["bottom"] - FOOT["top"]) * s, foot_d=FOOT["w"] * s,
        foot_ground_gap=(Y_GROUND - FOOT["bottom"]) * s,
        fin=fin, FIN_TIP_REACH_FRAC=u(FIN_TIP[1]) / R,
        FIN_ROOT_TOP_FRAC=(z(FIN_TOP[0]) - z0) / bh,
    )
    (HERE / "concept_fit.json").write_text(json.dumps(res, indent=1, default=float))
    print("fin_fit", {k: round(float(v), 3) for k, v in fin_fit.items()})
    for k, v in res.items():
        if isinstance(v, float):
            print(f"{k:24s} {v:8.3f}")
    print("body_profile", body_norm)
    print("cone_profile", cone_norm)
    print("fin", fin)


if __name__ == "__main__":
    main()
