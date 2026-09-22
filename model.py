"""
Geometry for the ATELIER rocket speaker.

`build(p)` takes the params module and returns a `Model` holding every part as
a separate build123d solid, plus the derived dimensions that the report and
renders need.

How the shape is made (plain-English version):
* The body and nose cone are "solids of revolution": we draw half of the side
  silhouette as a curve, then spin it 360 deg around the vertical axis.
* The body is hollowed by spinning a second curve that runs 2.5 mm inside
  the first and subtracting it.
* Front features (grille, bezel, recess) follow the body's curvature: they are
  thin bands a set distance in or out from the body surface, trimmed to a
  circle seen from the front.
* Fins are flat 2D outlines, thickened (tapering towards the tip), rounded,
  trimmed flush to the body surface and rotated to 60/180/300 deg.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

import numpy as np
from build123d import (
    Align,
    Axis,
    Box,
    Cylinder,
    Edge,
    Face,
    Location,
    Plane,
    Polyline,
    Pos,
    Rot,
    Solid,
    SlotOverall,
    Vector,
    Wire,
    extrude,
    fillet,
    revolve,
)

MIN = (Align.CENTER, Align.CENTER, Align.MIN)


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _xz(r, z):
    """A point in the XZ plane (the plane we draw side profiles in)."""
    return Vector(r, 0, z)


def _revolve_profile(pts_or_edges):
    """Close a list of edges into a face in the XZ plane and spin it around Z."""
    face = Face(Wire(pts_or_edges))
    return revolve(face, Axis.Z, 360)


def _front_cyl(radius, z, depth=400.0, y_from=0.0):
    """Cylinder along -Y (pointing out of the front), centred at height z.
    Spans y in [y_from - depth, y_from]."""
    return Pos(0, y_from, z) * Rot(90, 0, 0) * Cylinder(radius, depth, align=MIN)


def _dir(angle_deg):
    """Unit vector in the XY plane at an angle measured from the front (-Y)."""
    a = math.radians(angle_deg)
    return Vector(math.sin(a), -math.cos(a), 0)


def _one_solid(shape):
    """Return the largest solid from a boolean result (drops slivers)."""
    solids = shape.solids()
    if len(solids) == 1:
        return solids[0]
    return max(solids, key=lambda s: s.volume)


@dataclass
class Model:
    parts: dict = field(default_factory=dict)      # name -> Solid
    part_material_key: dict = field(default_factory=dict)  # name -> PART_MATERIALS key
    info: dict = field(default_factory=dict)       # derived dimensions and positions
    envelopes: dict = field(default_factory=dict)  # driver / battery envelopes (not parts)


# ---------------------------------------------------------------------------
# main build
# ---------------------------------------------------------------------------
def build(p) -> Model:
    m = Model()
    I = m.info

    # ---- vertical budget --------------------------------------------------
    H = p.OVERALL_HEIGHT
    R = p.BODY_MAX_DIA / 2
    z0 = p.BASE_CLEARANCE_FRAC * H                  # underside of the body
    bh = (H - z0) / (1 + p.CONE_HEIGHT_FRAC)        # body height
    ch = bh * p.CONE_HEIGHT_FRAC                    # cone height
    zt = z0 + bh                                    # cone joint
    I.update(H=H, R=R, z0=z0, body_h=bh, cone_h=ch, z_joint=zt)

    # ---- body side profile ------------------------------------------------
    rb = R * p.BODY_BOTTOM_DIA_FRAC
    rt = R * p.BODY_TOP_DIA_FRAC
    zm = z0 + bh * p.BODY_MAX_AT_FRAC
    # Upper and lower body are each r = R - (R - r_end) * s**n, where s runs
    # from 0 at the widest point to 1 at the end. n is the "fullness".
    nt, nb = p.BODY_TOP_FULLNESS, p.BODY_BOTTOM_FULLNESS
    prof = []
    for s in np.linspace(1, 0, 40, endpoint=False):          # bottom -> widest
        prof.append((R - (R - rb) * s ** nb, zm - s * (zm - z0)))
    for s in np.linspace(0, 1, 50):                          # widest -> top
        prof.append((R - (R - rt) * s ** nt, zm + s * (zt - zm)))
    # slope at the joint, continued by the nose cone
    a_top = math.atan((R - rt) * nt / (zt - zm))
    a_bot = math.atan((R - rb) * nb / (zm - z0))
    outer_curve = Edge.make_spline(
        [_xz(r, z) for r, z in prof],
        tangents=[Vector(math.cos(math.pi / 2 - a_bot), 0, math.sin(math.pi / 2 - a_bot)),
                  Vector(-math.sin(a_top), 0, math.cos(a_top))],
    )
    I.update(body_top_slope_deg=math.degrees(a_top))

    # Sample the curve so we can (a) offset it and (b) look up radius vs height.
    N = 160
    us = np.linspace(0, 1, N)
    pts = np.array([[outer_curve.position_at(u).X, outer_curve.position_at(u).Z] for u in us])
    tans = np.array([[outer_curve.tangent_at(u).X, outer_curve.tangent_at(u).Z] for u in us])
    normals = np.column_stack([tans[:, 1], -tans[:, 0]])  # outward normal in (r, z)
    if np.any(np.diff(pts[:, 1]) <= 0):
        raise ValueError("Body profile folds back on itself - check BODY_* parameters.")

    def r_out(z):
        return float(np.interp(z, pts[:, 1], pts[:, 0]))

    def offset_pts(d):
        """Profile points pushed d mm along the outward normal (negative = inward)."""
        return pts + d * normals

    inner = offset_pts(-p.WALL)

    def r_in(z):
        return float(np.interp(z, inner[:, 1], inner[:, 0], left=inner[0, 0], right=inner[-1, 0]))

    I.update(r_bottom=rb, r_top=rt, z_max=zm, r_in_top=inner[-1, 0], r_in_bottom=inner[0, 0])
    m._r_out, m._r_in = r_out, r_in  # handy for analysis

    def offset_solid(d, extend=0.0):
        """Solid of revolution bounded by the profile offset by d.
        extend > 0 continues the ends straight up/down (used to open the shell)."""
        q = offset_pts(d)
        q = q[q[:, 0] > 0.5]
        spline = Edge.make_spline([_xz(r, z) for r, z in q])
        zb, ztop = q[0, 1] - extend, q[-1, 1] + extend
        edges = [
            Edge.make_line(_xz(0, zb), _xz(q[0, 0], zb)),
        ]
        if extend > 0:
            edges.append(Edge.make_line(_xz(q[0, 0], zb), _xz(*q[0])))
        edges.append(spline)
        if extend > 0:
            edges.append(Edge.make_line(_xz(*q[-1]), _xz(q[-1, 0], ztop)))
        edges += [
            Edge.make_line(_xz(q[-1, 0], ztop), _xz(0, ztop)),
            Edge.make_line(_xz(0, ztop), _xz(0, zb)),
        ]
        return _revolve_profile(edges)

    def band(d_in, d_out):
        """A thin shell between two offsets of the body surface."""
        return offset_solid(d_out) - offset_solid(d_in)

    # ---- body shell --------------------------------------------------------
    outer_solid = _revolve_profile([
        Edge.make_line(_xz(0, z0), _xz(rb, z0)),
        outer_curve,
        Edge.make_line(_xz(rt, zt), _xz(0, zt)),
        Edge.make_line(_xz(0, zt), _xz(0, z0)),
    ])
    cavity = offset_solid(-p.WALL, extend=20)
    body = outer_solid - cavity
    m.envelopes["body_cavity"] = cavity & Pos(0, 0, z0) * Box(4 * R, 4 * R, bh, align=MIN)
    closed_bottom = p.SPLIT_MODE in ("nose", "fin_clamshell")
    if closed_bottom:
        floor = outer_solid & Pos(0, 0, z0) * Box(4 * R, 4 * R, p.WALL, align=MIN)
        body = body + floor
    battery_floor_z = z0 + (p.WALL if closed_bottom else p.FOOT_SPIGOT_HEIGHT)

    # ---- front: grille, bezel, recess, sound opening -----------------------
    zg = z0 + bh * p.GRILLE_Z_FRAC
    rg_body = r_out(zg)
    grille_r = p.GRILLE_DIA_FRAC * rg_body
    bezel_r = grille_r + p.BEZEL_WIDTH
    open_r = grille_r - p.GRILLE_LEDGE
    I.update(z_grille=zg, grille_dia=2 * grille_r, bezel_od=2 * bezel_r,
             sound_opening_dia=2 * open_r, body_dia_at_grille=2 * rg_body)

    recess_cut = band(-p.GRILLE_RECESS, 5.0) & _front_cyl(bezel_r, zg)
    body = body - recess_cut
    body = body - (_front_cyl(open_r, zg) & offset_solid(1.0))

    grille = band(-p.GRILLE_RECESS, -p.GRILLE_RECESS + p.GRILLE_THICK) & _front_cyl(grille_r - 0.1, zg)
    grille = _one_solid(grille)
    if p.HEX_PATTERN_ENABLED:
        grille = _cut_honeycomb(grille, grille_r - 0.1, zg, p)

    bezel = band(-p.GRILLE_RECESS, p.BEZEL_PROUD) & (
        _front_cyl(bezel_r - 0.1, zg) - _front_cyl(grille_r, zg)
    )
    bezel = _one_solid(bezel)

    # ---- driver mount (moulded into the body, behind the grille) ----------
    # The driver is too big to pass through the cone or collar openings, so it
    # is FRONT-loaded: with the grille and bezel off, it drops through the
    # sound opening into a round "well" and its frame screws onto a flat ring.
    # The grille then hides the screws.
    r_well = p.DRIVER_DIA / 2 + p.DRIVER_CLEARANCE
    ring_out = p.DRIVER_DIA / 2 + p.DRIVER_RING_WIDTH
    ring_in = p.DRIVER_DIA / 2 - p.DRIVER_FLANGE_WIDTH
    # The flat seating face sits just behind the innermost point of the curved
    # inner wall around the driver's rim, so the frame clears the wall.
    y_wall = []
    for th in np.linspace(0, 2 * math.pi, 72, endpoint=False):
        x, z = r_well * math.cos(th), zg + r_well * math.sin(th)
        ri = r_in(z)
        if ri > abs(x):
            y_wall.append(-math.sqrt(ri * ri - x * x))
    y_seat = max(y_wall) + 0.5
    y_back = y_seat + p.DRIVER_MOUNT_THICK
    inside = offset_solid(-p.WALL + 0.3)
    plate = _front_cyl(ring_out, zg, depth=p.DRIVER_MOUNT_THICK, y_from=y_back) & inside
    skirt = (_front_cyl(ring_out, zg, depth=200, y_from=y_seat)
             - _front_cyl(r_well, zg, depth=400, y_from=50)) & inside
    ring = (plate + skirt) - _front_cyl(ring_in, zg, depth=400, y_from=50)
    pcd = p.DRIVER_DIA / 2 - p.DRIVER_FLANGE_WIDTH / 2
    for k in range(p.DRIVER_SCREW_COUNT):
        th = math.radians(45 + k * 360 / p.DRIVER_SCREW_COUNT)
        ring = ring - Pos(pcd * math.cos(th), 0, pcd * math.sin(th)) * _front_cyl(
            p.DRIVER_SCREW_HOLE / 2, zg, depth=30, y_from=y_back + 1)
    body = body + ring
    driver_env = Pos(0, y_seat, zg) * Rot(-90, 0, 0) * Cylinder(
        p.DRIVER_DIA / 2, p.DRIVER_DEPTH, align=MIN)
    m.envelopes["driver"] = driver_env
    I.update(y_driver_seat=y_seat, driver_through_opening=(2 * open_r >= p.DRIVER_DIA + 2 * p.DRIVER_CLEARANCE))

    # ---- knob and LED ------------------------------------------------------
    z_bezel_bottom = zg - bezel_r
    kr = p.KNOB_DIA / 2
    zk = z_bezel_bottom - bh * p.KNOB_GAP_FRAC - kr
    z_led = (z_bezel_bottom + zk + kr) / 2
    y_surf = -r_out(zk)
    y_back = -max(r_out(z) for z in np.linspace(zk - kr, zk + kr, 9)) - p.KNOB_BODY_GAP
    y_face = y_surf - p.KNOB_PROUD
    knob = Pos(0, y_back, zk) * Rot(90, 0, 0) * Cylinder(kr, y_back - y_face, align=MIN)
    knob = fillet(knob.edges().sort_by(Axis.Y)[0], 1.0)            # rounded front edge
    knob = knob - Pos(0, y_back, zk) * Rot(90, 0, 0) * Cylinder(
        p.KNOB_SHAFT_DIA / 2, 8, align=MIN)                          # shaft bore
    knob = _one_solid(knob)
    body = body - _front_cyl(p.KNOB_SHAFT_HOLE / 2, zk, depth=30, y_from=-r_out(zk) + 15)
    body = body - _front_cyl(p.LED_DIA / 2, z_led, depth=30, y_from=-r_out(z_led) + 15)
    I.update(z_knob=zk, z_led=z_led)

    # ---- USB-C port --------------------------------------------------------
    zu = z0 + bh * p.USBC_Z_FRAC
    d = _dir(p.USBC_ANGLE_DEG)
    rot_z = p.USBC_ANGLE_DEG  # rotate a feature built facing -Y to face this angle
    port = extrude(
        Plane.XZ * SlotOverall(p.USBC_W, p.USBC_H), amount=30)  # along -Y
    port = Rot(0, 0, rot_z) * Pos(0, -r_out(zu) + 10, zu) * port
    pocket_depth = r_out(zu) - p.USBC_WALL_AT_PORT
    pocket = Pos(0, 0, zu) * Box(p.USBC_POCKET_W, pocket_depth, p.USBC_POCKET_H,
                                 align=(Align.CENTER, Align.MAX, Align.CENTER))
    pocket = Rot(0, 0, rot_z) * pocket
    pocket = pocket & offset_solid(-0.2)  # never break through the outside
    body = body - port - pocket
    I.update(z_usbc=zu)

    # ---- nose cone ---------------------------------------------------------
    straight = math.atan2(rt, ch)
    a_base = straight + p.CONE_OGIVE * (a_top - straight)
    a_tip = math.radians(p.CONE_TIP_HALF_ANGLE_DEG)
    ztip = zt + ch
    cone_curve = Edge.make_spline(
        [_xz(rt, zt), _xz(0, ztip)],
        tangents=[Vector(-math.sin(a_base), 0, math.cos(a_base)),
                  Vector(-math.sin(a_tip), 0, math.cos(a_tip))],
    )
    cone_outer = _revolve_profile([
        Edge.make_line(_xz(0, zt), _xz(rt, zt)),
        cone_curve,
        Edge.make_line(_xz(0, ztip), _xz(0, zt)),
    ])
    # hollow it: offset the cone profile inwards
    cu = np.linspace(0, 1, 80)
    cp = np.array([[cone_curve.position_at(u).X, cone_curve.position_at(u).Z] for u in cu])
    ct = np.array([[cone_curve.tangent_at(u).X, cone_curve.tangent_at(u).Z] for u in cu])
    cn = np.column_stack([ct[:, 1], -ct[:, 0]])
    ci = cp - p.CONE_WALL * cn
    ci = ci[(ci[:, 0] > 1.0) & (ci[:, 1] > zt + p.CONE_WALL)]
    shoulder = zt + p.CONE_WALL
    r_cav0 = float(np.interp(shoulder, ci[:, 1], ci[:, 0]))
    ci = ci[ci[:, 1] > shoulder + 0.5]
    cone_cavity = _revolve_profile([
        Edge.make_line(_xz(0, shoulder), _xz(r_cav0, shoulder)),
        Edge.make_spline([_xz(r_cav0, shoulder)] + [_xz(r, z) for r, z in ci]),
        Edge.make_line(_xz(*ci[-1]), _xz(0, ci[-1, 1])),
        Edge.make_line(_xz(0, ci[-1, 1]), _xz(0, shoulder)),
    ])
    spigot_r = r_in(zt) - p.FIT_CLEARANCE
    cone = cone_outer + Pos(0, 0, zt - p.CONE_SPIGOT_DEPTH) * Cylinder(
        spigot_r, p.CONE_SPIGOT_DEPTH + 0.5, align=MIN)
    cone = cone - cone_cavity - Pos(0, 0, zt - p.CONE_SPIGOT_DEPTH - 1) * Cylinder(
        spigot_r - p.CONE_SPIGOT_WALL, p.CONE_SPIGOT_DEPTH + 1 + p.CONE_WALL + 0.6, align=MIN)
    cone = _one_solid(cone)
    I.update(z_tip=ztip, cone_cavity_volume=cone_cavity.volume)
    m.envelopes["cone_cavity"] = cone_cavity

    # ---- foot + base collar ----------------------------------------------
    collar_h = z0 * p.COLLAR_HEIGHT_FRAC
    foot_r = p.BODY_MAX_DIA * p.FOOT_DIA_FRAC / 2
    collar = Pos(0, 0, z0 - collar_h) * Solid.make_cone(
        rb * 0.9, rb, collar_h)                       # slight taper, flush with the body at the top
    stub = Pos(0, 0, p.FOOT_GROUND_GAP) * Cylinder(
        foot_r, z0 - collar_h - p.FOOT_GROUND_GAP + 0.5, align=MIN)
    foot = collar + stub
    if not closed_bottom:
        foot = foot + Pos(0, 0, z0 - 0.5) * Cylinder(
            r_in(z0) - p.FIT_CLEARANCE, p.FOOT_SPIGOT_HEIGHT + 0.5, align=MIN)
    foot = _one_solid(fillet(foot.edges().sort_by(Axis.Z)[0], min(1.0, foot_r / 4)))
    I.update(foot_dia=2 * foot_r, collar_h=collar_h)

    # ---- fins --------------------------------------------------------------
    fins, tips = _build_fins(p, I, r_out, outer_solid, z0, bh, R)
    I["fin_tips"] = tips

    # ---- battery envelope -------------------------------------------------
    batt, batt_info = _place_battery(p, r_in, battery_floor_z, zt)
    m.envelopes["battery"] = batt
    I.update(batt_info)

    # ---- split the body ----------------------------------------------------
    body = _one_solid(body)
    if p.SPLIT_MODE == "fin_clamshell":
        a0 = p.FIN_ANGLE_OFFSET_DEG
        wedge_pts = [(0, 0)] + [
            (_dir(a).X * 400, _dir(a).Y * 400) for a in np.linspace(-a0, a0, 9)]
        wedge = Pos(0, 0, -10) * extrude(
            Face(Wire(Polyline(*wedge_pts, close=True).edges())), amount=H + 20)
        m.parts["body_front"] = _one_solid(body & wedge)
        m.parts["body_rear"] = _one_solid(body - wedge)
        m.part_material_key.update(body_front="body", body_rear="body")
    elif p.SPLIT_MODE in ("nose", "nose_tail"):
        m.parts["body"] = body
        m.part_material_key["body"] = "body"
    else:
        raise ValueError(f"Unknown SPLIT_MODE {p.SPLIT_MODE!r}")

    m.parts["nose_cone"] = cone
    for i, f in enumerate(fins):
        m.parts[f"fin_{i + 1}"] = f
        m.part_material_key[f"fin_{i + 1}"] = "fins"
    m.parts["foot"] = foot
    m.parts["grille"] = grille
    m.parts["bezel"] = bezel
    m.parts["knob"] = knob
    for k in ("nose_cone", "foot", "grille", "bezel", "knob"):
        m.part_material_key[k] = k
    return m


# ---------------------------------------------------------------------------
# fins
# ---------------------------------------------------------------------------
def _bezier(p0, p1, p2, n=40):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2)


def _build_fins(p, I, r_out, outer_solid, z0, bh, R):
    u_tip = p.FIN_TIP_REACH_FRAC * R
    z_rt = z0 + bh * p.FIN_ROOT_TOP_FRAC
    z_rb = z0 + bh * p.FIN_ROOT_BOTTOM_FRAC
    embed = 4.0  # start the outline inside the body, then trim flush
    top = (r_out(z_rt) - embed, z_rt)
    bot = (r_out(z_rb) - embed, z_rb)
    tip_out = (u_tip, 0.0)
    tip_in = (u_tip - p.FIN_TIP_FLAT, 0.0)

    # upper/outer edge: a curve from the body to the tip, bulging outward
    mid = ((top[0] + tip_out[0]) / 2, (top[1] + tip_out[1]) / 2)
    corner = (u_tip, z_rt)
    c1 = (mid[0] + p.FIN_OUTER_BULGE * (corner[0] - mid[0]),
          mid[1] + p.FIN_OUTER_BULGE * (corner[1] - mid[1]))
    upper = _bezier(top, c1, tip_out)
    # underside: an arch from the tip back up into the body
    mid2 = ((tip_in[0] + bot[0]) / 2, (tip_in[1] + bot[1]) / 2)
    corner2 = (tip_in[0], bot[1])      # arch rises steeply near the tip
    c2 = (mid2[0] + p.FIN_UNDERCUT * (corner2[0] - mid2[0]),
          mid2[1] + p.FIN_UNDERCUT * (corner2[1] - mid2[1]))
    lower = _bezier(tip_in, c2, bot)

    # Build the outline in the XZ plane (fin points along +X), thickness along Y
    e_upper = Edge.make_spline([_xz(x, z) for x, z in upper])
    e_lower = Edge.make_spline([_xz(x, z) for x, z in lower])
    outline = Wire([
        e_upper,
        Edge.make_line(_xz(*tip_out), _xz(*tip_in)),
        e_lower,
        Edge.make_line(_xz(*bot), _xz(*top)),
    ])
    T0, T1 = p.FIN_ROOT_THICK, p.FIN_TIP_THICK
    slab = extrude(Face(outline), amount=T0 / 2, both=True)
    # taper: intersect with a wedge that is T0 thick at the body and T1 at the tip
    r_ref = r_out(z_rt)
    wedge_pts = [(0, -T0 / 2), (r_ref, -T0 / 2), (u_tip + 1, -T1 / 2),
                 (u_tip + 1, T1 / 2), (r_ref, T0 / 2), (0, T0 / 2)]
    wedge = Pos(0, 0, -5) * extrude(Face(Wire(Polyline(*wedge_pts, close=True).edges())),
                                    amount=z_rt + 20)
    blank = _one_solid(slab & wedge)
    for rad in (p.FIN_EDGE_FILLET, p.FIN_EDGE_FILLET * 0.6, p.FIN_EDGE_FILLET * 0.3):
        try:
            # round every edge except the straight root line (which gets trimmed anyway)
            edges = [e for e in blank.edges() if e.center().X > r_ref - embed + 1.5]
            blank = _one_solid(fillet(edges, rad))
            break
        except Exception:
            continue
    blank = _one_solid(blank - outer_solid)

    fins, tips = [], []
    n = p.FIN_COUNT
    for k in range(n):
        ang = p.FIN_ANGLE_OFFSET_DEG + k * 360 / n
        fins.append(Rot(0, 0, ang - 90) * copy.deepcopy(blank))  # own copy so STEP keeps separate names
        d = _dir(ang)
        u_c = u_tip - p.FIN_TIP_FLAT / 2
        tips.append((d.X * u_c, d.Y * u_c))
    I.update(fin_tip_reach=u_tip, z_fin_root_top=z_rt, z_fin_root_bottom=z_rb)
    return fins, tips


# ---------------------------------------------------------------------------
# battery
# ---------------------------------------------------------------------------
def _place_battery(p, r_in, z_floor, z_top):
    """Try the battery box in each orientation; keep the one whose centre is lowest."""
    L, W, T = p.BATTERY_SIZE
    best = None
    for (h, a, b) in ((T, L, W), (W, L, T), (L, W, T)):
        half_diag = math.hypot(a, b) / 2 + p.BATTERY_CLEARANCE
        zb = z_floor
        while zb + h < z_top:
            zs = np.linspace(zb, zb + h, 12)
            if all(r_in(z) >= half_diag for z in zs):
                break
            zb += 0.5
        else:
            continue
        if best is None or zb + h / 2 < best[0] + best[1] / 2:
            best = (zb, h, a, b)
    if best is None:
        raise ValueError("Battery does not fit in the body in any orientation.")
    zb, h, a, b = best
    box = Pos(0, 0, zb) * Box(a, b, h, align=MIN)
    return box, dict(battery_z_bottom=zb, battery_z_centre=zb + h / 2,
                     battery_min_opening=min(math.hypot(L, W), math.hypot(L, T), math.hypot(W, T)),
                     battery_orientation=f"{a:g} x {b:g} footprint, {h:g} tall")


# ---------------------------------------------------------------------------
# honeycomb
# ---------------------------------------------------------------------------
def _cut_honeycomb(grille, radius, zg, p):
    """Punch a hexagonal hole pattern through the (curved) grille, along Y."""
    from build123d import RegularPolygon, Compound
    pitch = p.HEX_HOLE + p.HEX_WEB
    dx = pitch
    dz = pitch * math.sqrt(3) / 2
    hex_r = p.HEX_HOLE / math.sqrt(3)       # circumradius from across-flats
    limit = radius - p.HEX_WEB - hex_r
    tools = []
    base = extrude(Plane.XZ * RegularPolygon(hex_r, 6, major_radius=True, rotation=30), amount=120, both=True)
    j = 0
    z = -limit
    while z <= limit + 1e-6:
        off = (dx / 2) if (j % 2) else 0.0
        x = -limit - off
        while x <= limit + 1e-6:
            if math.hypot(x, z) <= limit:
                tools.append(Pos(x, 0, zg + z) * base)
            x += dx
        z += dz
        j += 1
    return _one_solid(grille - Compound(tools))
