"""Trace the Faro logo's grooves from the reference image and fit smooth curves to them.

Writes brand/logo/bathsheva_emblem_curves.json, the curves the master artwork is built from
(app/factory/logo.py; export with scripts/export_nameplate_artwork.py). Everything is measured in
reference-image pixels (y down) and the frame (axis, centre, radius) is stored with the curves.

Method: the reference is a photographed metal medallion of raised plates separated by dark grooves.
Across each groove (arcs for the rays, radial lines for the sun ring, columns for the horizon, wedges
and waves) the luminance profile is sampled, and each plate edge is where the profile crosses 75 % of
the neighbouring plate's brightness. The groove centre is midway between its two edges and its width
is the distance between them. Smooth curves are then fitted: cubic angle-vs-radius for the ray
grooves, circles for the sun and its ring, a cosine series for the waves, a quartic for the lower
edge of the lowest rays, a shallow parabola for the top of the horizon band. Left and right samples
are pooled (mirrored) so the master is symmetric.

Needs numpy, scipy and Pillow (all in the backend venv). Usage, from the repo root:
    backend/.venv/bin/python scripts/trace_logo.py
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "backend" / "seed" / "artwork" / "reference" / "logo_reference.webp"
OUT = ROOT / "brand" / "logo" / "bathsheva_emblem_curves.json"

# Symmetry axis (px). The sun and rays are symmetric about x ≈ 643.5, the waves about x ≈ 645 and the
# medallion's own outline is centred near x ≈ 648; 645 gave the best edge agreement overall.
AXIS_X = 645.0
EDGE_FRACTION = 0.75  # plate edge: where the profile crosses this fraction of the plate brightness
# The 75 % rule puts edges about 0.7 px into the plates on average (measured against the image along
# the whole outline), so the fitted ray and wave groove widths are reduced by this much.
WIDTH_BIAS_PX = 1.4
SUN_PIVOT = (643.3, 751.0)  # pivot for the ray-groove sampling arcs (near the sun's centre)
RAY_GROOVES_DEG = (27.5, 52.0, 77.5, 102.5, 126.5, 150.5)  # approximate, about the pivot; refined by tracing
MIRROR_PAIRS = ((27.5, 150.5), (52.0, 126.5), (77.5, 102.5))


def load():
    im = np.asarray(Image.open(REFERENCE).convert("RGBA")).astype(float)
    lum = gaussian_filter(im[..., :3].mean(axis=2), 2.5)
    return lum, im[..., 3] > 128


def edges(v, k0):
    """Plate edges either side of the dark groove nearest index k0 of profile v: (lo, hi) fractional
    indices, or None when there is no clear groove."""
    n = len(v)
    lo_w = max(0, k0 - 12)
    km = lo_w + int(np.argmin(v[lo_w:min(n, k0 + 13)]))
    if v[km] > 70:
        return None
    res = []
    for d in (-1, 1):
        k = km
        while True:
            k += d
            if k < 0 or k >= n:
                return None
            if v[k] > 95 and all(0 <= k + d * j < n and v[k + d * j] > 85 for j in range(1, 5)):
                plate = np.median([v[k + d * j] for j in range(2, 10) if 0 <= k + d * j < n])
                thr = EDGE_FRACTION * plate
                kk = k
                while v[kk] > thr:
                    kk -= d
                a, b = v[kk], v[kk + d]
                res.append(kk + d * ((thr - a) / (b - a) if b != a else 0.0))
                break
    return res[0], res[1]


def fit_circle(pts):
    p = np.asarray(pts, float)
    a = np.c_[2 * p, np.ones(len(p))]
    s = np.linalg.lstsq(a, (p ** 2).sum(1), rcond=None)[0]
    r = float(np.sqrt(s[2] + s[0] ** 2 + s[1] ** 2))
    return float(s[0]), float(s[1]), r, float(np.std(np.hypot(p[:, 0] - s[0], p[:, 1] - s[1]) - r))


def medallion(lum, alpha):
    """Outer circle through the plates' outer ends (the photo's outline is about 0.8 % out of round)."""
    pts = []
    for adeg in np.arange(0, 360, 2.0):
        a = np.radians(adeg)
        rr = np.arange(480, 600, 0.25)
        xs, ys = AXIS_X + rr * np.cos(a), 618.37 - rr * np.sin(a)
        v = map_coordinates(lum, [ys, xs], order=1)
        plate = np.median(v[:60])
        if plate < 95:
            continue
        k = np.nonzero(v < 0.6 * plate)[0]
        if len(k):
            pts.append((xs[k[0]], ys[k[0]]))
    pts = np.array(pts)
    cx, cy, r, _ = fit_circle(pts)
    keep = np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - r) < 10
    cx, cy, r, rms = fit_circle(pts[keep])
    return cx, cy, r, rms


def ray_grooves(lum, rim):
    mx, my, mr = rim[:3]
    sx, sy = SUN_PIVOT
    out = {}
    for c in RAY_GROOVES_DEG:
        rows = []
        for r in np.arange(292, 700, 2.0):
            th = np.arange(np.radians(c - 9), np.radians(c + 9), 0.5 / r)
            xs, ys = sx + r * np.cos(th), sy - r * np.sin(th)
            inside = np.hypot(xs - mx, ys - my) < mr - 14
            v = map_coordinates(lum, [ys, xs], order=1)
            g = np.radians(rows[-1][1]) if rows else np.radians(c)
            e = edges(v, int(np.argmin(np.abs(th - g))))
            if e is None:
                continue
            lo, hi = e
            if not (inside[int(lo)] and inside[min(int(np.ceil(hi)), len(th) - 1)]):
                break
            idx = np.arange(len(th))
            tlo, thi = np.interp(lo, idx, th), np.interp(hi, idx, th)
            w = (thi - tlo) * r
            if 20 < w < 75:
                rows.append((r, np.degrees((tlo + thi) / 2), w))
        out[c] = np.array(rows)
    fits = []
    for a, b in MIRROR_PAIRS:
        pts, ws = [], []
        for key, mirror in ((a, False), (b, True)):
            d = out[key]
            d = d[d[:, 2] > 0.8 * np.median(d[:, 2])]  # drop samples where the rim interferes
            t = np.radians(d[:, 1])
            x, y = sx + d[:, 0] * np.cos(t), sy - d[:, 0] * np.sin(t)
            if mirror:
                x = 2 * AXIS_X - x
            pts.append(np.c_[x, y])
            ws.append(d[:, [0, 2]])
        p, w = np.vstack(pts), np.vstack(ws)
        rr = np.hypot(p[:, 0] - AXIS_X, SUN_PIVOT[1] - p[:, 1])
        th = np.arctan2(SUN_PIVOT[1] - p[:, 1], p[:, 0] - AXIS_X)
        c = np.polyfit(rr, th, 3)
        cw = np.polyfit(w[:, 0], w[:, 1], 1)
        cw[1] -= WIDTH_BIAS_PX
        rms = float(((np.polyval(c, rr) - th) * rr).std())
        fits.append({"theta_poly": c.tolist(), "width_poly": cw.tolist(), "r_range": [float(rr.min()), float(rr.max())],
                     "rms_px": round(rms, 2)})
    return fits


def sun(lum):
    inner, outer = [], []
    for adeg in np.arange(3, 177.5, 0.5):
        if min(abs(adeg - k) for k in (26.5, 53.8, 78.4, 101.4, 125.9, 153.6)) < 6:
            continue  # skip where the ray grooves join
        a = np.radians(adeg)
        rr = np.arange(200, 330, 0.5)
        xs, ys = SUN_PIVOT[0] + rr * np.cos(a), 765 - rr * np.sin(a)
        e = edges(map_coordinates(lum, [ys, xs], order=1), int(np.argmin(np.abs(rr - 265))))
        if e is None:
            continue
        idx = np.arange(len(rr))
        ri, ro = np.interp(e[0], idx, rr), np.interp(e[1], idx, rr)
        if 15 < ro - ri < 50:
            inner.append((SUN_PIVOT[0] + ri * np.cos(a), 765 - ri * np.sin(a)))
            outer.append((SUN_PIVOT[0] + ro * np.cos(a), 765 - ro * np.sin(a)))
    return fit_circle(inner), fit_circle(outer)


def columns(lum, alpha):
    """Every groove crossing on vertical lines through the lower half: {x: [(top, bottom), ...]}."""
    a_f = alpha.astype(float)
    cols = {}
    for x in np.arange(90, 1210, 2.0):
        ys = np.arange(640, 1120, 0.5)
        v = map_coordinates(lum, [ys, np.full_like(ys, x)], order=1)
        f = map_coordinates(a_f, [ys, np.full_like(ys, x)], order=1)
        used = np.zeros(len(v), bool)
        found = []
        for km in np.argsort(v):
            if v[km] > 60:
                break
            if used[km] or f[km] < 0.5:
                continue
            e = edges(v, km)
            if e is None:
                used[max(0, km - 4):km + 5] = True
                continue
            used[int(e[0]):int(np.ceil(e[1])) + 1] = True
            idx = np.arange(len(ys))
            found.append((float(np.interp(e[0], idx, ys)), float(np.interp(e[1], idx, ys))))
        cols[float(x)] = sorted(found)
    return cols


def main():
    lum, alpha = load()
    rim = medallion(lum, alpha)
    print(f"medallion outline: centre ({rim[0]:.1f}, {rim[1]:.1f}) r {rim[2]:.1f} px, rms {rim[3]:.1f} px")
    rays = ray_grooves(lum, rim)
    (six, siy, sir, sirms), (sox, soy, sor, sorms) = sun(lum)
    cols = columns(lum, alpha)
    hz, w1, w2 = [], [], []
    for x, runs in cols.items():
        for a, b in runs:
            if 735 < b < 765:
                hz.append((x, a, b))
            elif 790 < a < 900 and 30 < b - a < 50:
                w1.append((x, a, b))
            elif 900 < a < 1010 and 30 < b - a < 50:
                w2.append((x, a, b))
    hz = np.array(hz)
    d = hz[:, 0] - AXIS_X
    # Sun's lower edge (straight) and the top of the horizon band (a very shallow bow, as in the image).
    under_sun = (np.abs(d) < 240) & (hz[:, 1] > 735)
    sun_chord = float(np.median(hz[under_sun, 1]))
    m = np.abs(d) < 560
    band = np.polyfit(d[m] ** 2, hz[m, 2], 1)
    # Lower edge of the lowest rays (the dark wedge's top), against distance from the axis.
    ad = np.abs(d)
    m = (ad > 300) & (ad < 545) & (hz[:, 1] < 740)
    wedge = np.polyfit(ad[m], hz[m, 1], 4)
    wedge_rms = float((np.polyval(wedge, ad[m]) - hz[m, 1]).std())
    waves = []
    for runs in (w1, w2):
        r = np.array(runs)
        x, y, wv = r[:, 0], (r[:, 1] + r[:, 2]) / 2, r[:, 2] - r[:, 1]
        keep = (x > 150) & (x < 1150)
        x, y, wv = x[keep], y[keep], wv[keep]
        xm = np.abs(x - AXIS_X)

        def f(p, xm):
            a0, a1, k, a2 = p
            return a0 + a1 * np.cos(k * xm) + a2 * np.cos(2 * k * xm)

        p = least_squares(lambda p: f(p, xm) - y, [840, 27, 2 * np.pi / 510, 0]).x
        slope = -p[1] * p[2] * np.sin(p[2] * xm) - 2 * p[3] * p[2] * np.sin(2 * p[2] * xm)
        width = float(np.median(wv * np.cos(np.arctan(slope)))) - WIDTH_BIAS_PX
        waves.append({"coeffs": p.tolist(), "width": width, "rms_px": round(float((f(p, xm) - y).std()), 2)})
    curves = {
        "description": "Faro logo: groove curves traced from backend/seed/artwork/reference/logo_reference.webp "
                       "by scripts/trace_logo.py. Units: reference-image pixels, y down.",
        "frame": {"axis_x": AXIS_X, "centre_y": rim[1], "radius": rim[2]},
        "sun": {"cy": siy, "r": sir, "rms_px": round(sirms, 2)},
        "sun_ring_outer": {"cy": soy, "r": sor, "rms_px": round(sorms, 2)},
        "sun_chord_y": sun_chord,
        "horizon_band_top": {"c0": float(band[1]), "c2": float(band[0])},
        "ray_pivot": [AXIS_X, SUN_PIVOT[1]],
        "ray_grooves": rays,
        "wedge_top": {"poly": wedge.tolist(), "d_max": float(ad[m].max()), "rms_px": round(wedge_rms, 2)},
        "wave_grooves": waves,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(curves, indent=1) + "\n")
    print(f"sun r {sir:.1f} (rms {sirms:.2f}), ring r {sor:.1f} (rms {sorms:.2f}), chord y {sun_chord:.1f}")
    print("ray grooves rms px:", [f["rms_px"] for f in rays], " waves rms px:", [w["rms_px"] for w in waves],
          f" wedge rms {wedge_rms:.2f}")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
