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
    Circle,
    Cylinder,
    Edge,
    Ellipse,
    Face,
    GeomType,
    Kind,
    offset,
    chamfer,
    Location,
    Plane,
    Polygon,
    Polyline,
    Pos,
    RectangleRounded,
    Rot,
    Solid,
    Sphere,
    SlotOverall,
    Vector,
    Wire,
    extrude,
    fillet,
    revolve,
    sweep,
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


def _smooth_spline(points):
    """Smooth B-spline within 0.01 mm of the points (robust in booleans)."""
    return Edge.make_spline_approx(points, tol=0.01, max_deg=5)


def _front_cyl(radius, z, depth=400.0, y_from=0.0):
    """Cylinder along -Y (pointing out of the front), centred at height z.
    Spans y in [y_from - depth, y_from]."""
    return Pos(0, y_from, z) * Rot(90, 0, 0) * Cylinder(radius, depth, align=MIN)


def _dir(angle_deg):
    """Unit vector in the XY plane at an angle measured from the front (-Y)."""
    a = math.radians(angle_deg)
    return Vector(math.sin(a), -math.cos(a), 0)


def _port_frame(p, F):
    """Location of the collar USB-C port: origin at the port face centre F, local
    Z pointing out of the port (outward and down), local X horizontal."""
    u = _dir(p.USBC_ANGLE_DEG)
    t = math.radians(p.USBC_TILT_DEG)
    a = u * math.cos(t) - Vector(0, 0, 1) * math.sin(t)
    return Location(Plane(origin=F, x_dir=Vector(-u.Y, u.X, 0), z_dir=a)), u, a


def _collar_usb_port(p, I, m, collar, cup_edge, z0, z_cb):
    """Sealed USB-C port in the gold collar cup, facing down between two fins.
    Cuts a flat-bottomed recess (so a standard plug's overmold seats square on
    the port face), the receptacle opening and a pocket behind it for the
    receptacle and its small board. The face is put as low as possible (best
    hidden) while the plug's rigid overmold still clears the ground. Also makes
    the plug + cable envelopes used for the fit checks and the render."""
    ow, oh, ol = p.USBC_PLUG_OVERMOLD
    t = math.radians(p.USBC_TILT_DEG)
    c = p.USBC_RECESS_CLEAR
    # cup radius vs height
    samples = sorted((q.Z, q.X) for q in (cup_edge.position_at(k / 200) for k in range(201)))
    zs_, rs_ = np.array([q[0] for q in samples]), np.array([q[1] for q in samples])
    wall = p.USBC_WALL_AT_PORT
    pw, ph, dep = p.USBC_COLLAR_POCKET
    u = _dir(p.USBC_ANGLE_DEG)

    def walled(F):
        """True if the pocket and the port face have at least `wall` of zinc
        round them (the face must not run out of the steep cup at its top)."""
        loc_, _, _ = _port_frame(p, F)
        env = loc_ * Pos(0, 0, -2 * wall - dep) * Box(
            max(pw, ow + 2 * c) + 2 * wall, max(ph, oh + 2 * c) + 2 * wall, 2 * wall + dep,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        r = env - collar
        return r is None or r.volume < 0.01

    face_z = None
    for z_s in np.arange(z_cb + oh / 2, z0 - oh / 2, 0.5):
        r_s = float(np.interp(z_s, zs_, rs_))
        for depth in np.arange(c, 6.0, 0.25):          # sink the face until it's fully walled
            rF, zF = r_s - depth * math.cos(t), z_s + depth * math.sin(t)
            lowest = zF - ol * math.sin(t) - oh / 2 * math.cos(t)
            if lowest < p.USBC_PLUG_GROUND_CLEAR:
                continue                               # a deeper face sits higher
            F = Vector(u.X * rF, u.Y * rF, zF)
            if walled(F):
                face_z = (rF, zF, lowest, depth)
                break
        if face_z is not None:
            break
    if face_z is None:
        raise ValueError("No spot on the collar cup where the USB-C port is walled and the plug clears the ground")
    rF, zF, lowest, depth = face_z
    F = Vector(u.X * rF, u.Y * rF, zF)
    loc, u, a = _port_frame(p, F)
    recess = loc * extrude(RectangleRounded(ow + 2 * c, oh + 2 * c, min(2.5, oh / 2 - 0.1) + c), amount=40)
    opening = loc * Pos(0, 0, -wall - 0.5) * extrude(SlotOverall(p.USBC_W, p.USBC_H), amount=wall + 1.0)
    pocket = loc * Pos(0, 0, -wall - dep) * Box(pw, ph, dep, align=(Align.CENTER, Align.CENTER, Align.MIN))
    breakout = (pocket - collar).volume                  # pocket must stay inside the collar
    out = _one_solid(collar - recess - opening - pocket)
    rw, rh, rl = p.USBC_RECEPTACLE
    m.envelopes["usb_receptacle"] = loc * Pos(0, 0, -wall - rl + 1.0) * Box(
        rw, rh, rl - 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # plug: tongue in the receptacle and the rigid overmold, then the flexible
    # strain relief + cable, which bends down onto the ground and runs out
    # between the fins
    tongue = loc * Pos(0, 0, -6.65) * Box(8.25, 2.4, 6.65, align=(Align.CENTER, Align.CENTER, Align.MIN))
    over = loc * extrude(RectangleRounded(ow, oh, min(2.5, oh / 2 - 0.1)), amount=ol)
    rd, rlen = p.USBC_PLUG_RELIEF
    cr = p.USBC_CABLE_DIA / 2
    P0 = F + a * ol
    s_ = (P0.Z - rd / 2) / math.sin(t)                 # straight on to where it meets the ground
    C = P0 + a * s_
    C = Vector(C.X, C.Y, rd / 2)
    P2 = C + u * s_
    P3 = P2 + u * 60
    path = Wire([Edge.make_bezier(P0, C, P2), Edge.make_line(P2, P3)])
    relief = sweep(Plane(origin=P0, z_dir=a) * Circle(rd / 2), path=Wire([path.edges()[0].trim_to_length(
        0, min(rlen, 0.999 * path.edges()[0].length))]))
    cable = sweep(Plane(origin=P0, z_dir=a) * Circle(cr), path=path)
    m.envelopes["usb_plug"] = _one_solid(tongue + over)
    # right-angle plug (as shipped): a short head, then a boot leaving sideways.
    # Local +Y points up the port face (up and out), +X is horizontal.
    hl = p.USBC_RA_HEAD_LEN
    bw, bl = p.USBC_RA_BOOT
    head = extrude(RectangleRounded(ow, oh, min(2.5, oh / 2 - 0.1)), amount=hl)
    ra = {}
    for name, rot in (("up", 0), ("down", 180), ("side A (towards the rear fin)", -90),
                      ("side B (towards the side fin)", 90)):
        across = oh if rot in (90, -90) else bw
        boot = Pos(0, 0, hl - oh) * Rot(0, 0, rot) * Box(across, bl, oh, align=(Align.CENTER, Align.MIN, Align.MIN))
        ra[name] = loc * (head + boot)
    m._usb_right_angle = ra
    m.envelopes["usb_cable"] = cable + relief
    # wire channel starts at the back of the pocket
    m._usb_pocket_back = F - a * (wall + dep - 0.5)
    m._usb_axis = a
    I.update(usbc_face=(F.X, F.Y, F.Z), usbc_face_r=rF, usbc_plug_lowest=lowest, usbc_face_depth=depth,
             usbc_pocket_breakout=breakout)
    return out


def _safe_cut(body, tool, label=""):
    """body - tool, checked: raises if OpenCascade returns an empty, invalid or
    inside-out solid (volume integration on spline faces is only good to
    ~0.5 %, so small volume differences are allowed)."""
    v0 = body.volume
    out = body - tool
    if not (out.is_valid and 0.9 * v0 < out.volume < 1.01 * v0):
        raise RuntimeError(f"Boolean cut failed: {label}")
    return out


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
    print_parts: dict = field(default_factory=dict)  # print-only variants (e.g. thicker grille webs)


# ---------------------------------------------------------------------------
# main build
# ---------------------------------------------------------------------------
def build(p, visual_only=False) -> Model:
    """visual_only=True skips everything hidden inside (driver mount, fin bolt
    holes, fin hollowing, ballast, chassis, fit checks) for fast previews."""
    m = Model()
    I = m.info

    # ---- vertical budget --------------------------------------------------
    H = p.OVERALL_HEIGHT
    R = p.BODY_MAX_DIA / 2
    z0_ref = p.BASE_CLEARANCE_FRAC * H              # underside of the body (styling value)
    z0 = z0_ref
    base_pr = p.PR_POSITION == "base"
    no_pr = p.PR_POSITION == "none"                 # sealed enclosure, no passive radiator
    if p.PR_POSITION not in ("base", "rear", "none"):
        raise ValueError(f"Unknown PR_POSITION {p.PR_POSITION!r}")
    base_nozzle = base_pr and p.BASE_STYLE == "nozzle"
    base_vent = base_pr and p.BASE_STYLE == "vent"
    concept_base = base_vent or no_pr               # the concept's gold cup + small foot
    if base_pr and p.BASE_STYLE not in ("vent", "nozzle"):
        raise ValueError(f"Unknown BASE_STYLE {p.BASE_STYLE!r}")
    if base_nozzle:
        # A down-firing radiator breathes out through a hole in the collar, then
        # sideways through the gap between the collar and the foot stub. That gap
        # must pass at least PR_EXIT_AREA_RATIO x the radiator's area, so the foot
        # stub hangs lower on posts and the body may have to rise to make room.
        collar_h_ref = z0_ref * p.COLLAR_HEIGHT_FRAC
        r_hole = p.PR_BASE_EFFECTIVE_DIA / 2 + 1.0
        sd = math.pi * (p.PR_BASE_EFFECTIVE_DIA / 2) ** 2
        # mesh ring just inside the collar's lower edge; add honeycomb rows until
        # the open (hole) area reaches PR_EXIT_AREA_RATIO x the radiator area
        r_mesh_out = R * p.BODY_BOTTOM_DIA_FRAC * 0.9 - p.BASE_MESH_INSET
        r_mesh_mid = r_mesh_out - p.GRILLE_THICK / 2
        n_around, _ = _hex_ring_counts(r_mesh_mid, 0.0, p)
        hex_area = math.sqrt(3) / 2 * p.HEX_HOLE ** 2
        rows = max(1, math.ceil(p.PR_EXIT_AREA_RATIO * sd / (n_around * hex_area)))
        pitch = p.HEX_HOLE + p.HEX_WEB
        perf_h = 2 * p.HEX_HOLE / math.sqrt(3) + (rows - 1) * pitch * math.sqrt(3) / 2 + 2 * p.HEX_WEB
        plenum = perf_h + 2 * p.BASE_MESH_LAND
        z0 = max(z0_ref, p.FOOT_GROUND_GAP + p.FOOT_NOZZLE_HEIGHT + plenum + collar_h_ref)
        I.update(pr_sd=sd, pr_hole_dia=2 * r_hole, pr_plenum=plenum, mesh_rows=rows,
                 mesh_holes=rows * n_around, pr_exit_area=rows * n_around * hex_area,
                 mesh_dia=2 * r_mesh_out)
    I["z0_ref"] = z0_ref
    bh = (H - z0) / (1 + p.CONE_HEIGHT_FRAC)        # body height
    ch = bh * p.CONE_HEIGHT_FRAC                    # cone height
    zt = z0 + bh                                    # cone joint
    I.update(H=H, R=R, z0=z0, body_h=bh, cone_h=ch, z_joint=zt)

    # ---- body side profile ------------------------------------------------
    if p.BODY_PROFILE_MODE == "points":
        # measured profile (fractions of body height and max radius), joined
        # with a shape-preserving interpolation so it never overshoots
        from scipy.interpolate import PchipInterpolator
        tt = np.array([q[0] for q in p.BODY_PROFILE_POINTS], dtype=float)
        rr = np.array([q[1] for q in p.BODY_PROFILE_POINTS], dtype=float)
        f = PchipInterpolator(tt, rr)
        ts = (1 - np.cos(np.linspace(0, math.pi, 90))) / 2        # denser at both ends
        prof = [(R * float(f(t)), z0 + t * bh) for t in ts]
        rb, rt = R * rr[0], R * rr[-1]
        zm = z0 + bh * tt[int(np.argmax(rr))]
        a_top = math.atan(-R * float(f(1.0, 1)) / bh)
        d0 = R * float(f(0.0, 1)) / bh                              # dr/dz at the bottom
        slope_bot = d0
        # an approximating spline (within 0.01 mm) rather than one forced through
        # every point: the interpolated one has tiny ripples that made OpenCascade
        # fail on small holes (LED, knob) at unlucky heights
        outer_curve = _smooth_spline([_xz(r, z) for r, z in prof])
    else:
        rb = R * p.BODY_BOTTOM_DIA_FRAC
        rt = R * p.BODY_TOP_DIA_FRAC
        zm = z0 + bh * p.BODY_MAX_AT_FRAC
        # Upper and lower body are each r = R - (R - r_end) * s**n, where s runs
        # from 0 at the widest point to 1 at the end. n is the "fullness".
        nt, nb = p.BODY_TOP_FULLNESS, p.BODY_BOTTOM_FULLNESS
        prof = []
        for s_ in np.linspace(1, 0, 40, endpoint=False):         # bottom -> widest
            prof.append((R - (R - rb) * s_ ** nb, zm - s_ * (zm - z0)))
        for s_ in np.linspace(0, 1, 50):                         # widest -> top
            prof.append((R - (R - rt) * s_ ** nt, zm + s_ * (zt - zm)))
        # slope at the joint, continued by the nose cone
        a_top = math.atan((R - rt) * nt / (zt - zm))
        a_bot = math.atan((R - rb) * nb / (zm - z0))
        slope_bot = math.tan(a_bot)
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

    r_open_bot = min(inner[0, 0], rb - p.BODY_BOTTOM_LAND)     # bottom opening radius
    I.update(r_bottom=rb, r_top=rt, z_max=zm, r_in_top=inner[-1, 0], r_in_bottom=r_open_bot)
    m._r_out, m._r_in = r_out, r_in  # handy for analysis

    def offset_solid(d, extend=0.0):
        """Solid of revolution bounded by the profile offset by d.
        extend > 0 continues the ends straight up/down (used to open the shell)."""
        q = offset_pts(d)
        q = q[q[:, 0] > 0.5]
        spline = _smooth_spline([_xz(r, z) for r, z in q])
        zb, ztop = q[0, 1] - extend, q[-1, 1] + extend
        edges = [
            Edge.make_line(_xz(0, zb), _xz(q[0, 0], zb)),
        ]
        if extend > 0:
            # bottom opening no wider than r_bottom - BODY_BOTTOM_LAND, leaving a
            # flat land round it (matters for a flat-bottomed profile)
            x_open = min(q[0, 0], rb - p.BODY_BOTTOM_LAND)
            edges[0] = Edge.make_line(_xz(0, zb), _xz(x_open, zb))
            edges.append(Edge.make_line(_xz(x_open, zb), _xz(x_open, q[0, 1])))
            if x_open < q[0, 0] - 1e-6:
                edges.append(Edge.make_line(_xz(x_open, q[0, 1]), _xz(*q[0])))
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

    def front_outline(rad):
        """Prism along -Y for a grille feature of 'radius' rad. With
        GRILLE_WRAPPED the circle is wrapped round the curved body (as in the
        concept): full height, but narrower when seen from the front."""
        if not p.GRILLE_WRAPPED:
            return _front_cyl(rad, zg)
        a = rg_body * math.sin(min(rad / rg_body, math.pi / 2))
        return Pos(0, 0, zg) * extrude(Plane.XZ * Ellipse(a, rad), amount=400)

    grille_a = rg_body * math.sin(min(grille_r / rg_body, math.pi / 2)) if p.GRILLE_WRAPPED else grille_r
    open_r = min(open_r, grille_a - p.GRILLE_LEDGE)          # round sound opening fits inside
    I.update(sound_opening_dia=2 * open_r, grille_front_width=2 * grille_a)
    recess_cut = band(-p.GRILLE_RECESS, 5.0) & front_outline(bezel_r)
    body = body - recess_cut
    body = body - (_front_cyl(open_r, zg) & offset_solid(1.0))

    grille = band(-p.GRILLE_RECESS, -p.GRILLE_RECESS + p.GRILLE_THICK) & front_outline(grille_r - 0.1)
    grille = _one_solid(grille)
    if p.HEX_PATTERN_ENABLED:
        blank = grille
        grille = _cut_honeycomb(blank, (grille_a - 0.1, grille_r - 0.1), zg, p)
        if getattr(p, "PRINT_HEX_WEB", p.HEX_WEB) != p.HEX_WEB:
            # the printed prototype grille: same holes, thicker webs (resin minimum)
            import types
            pp = types.SimpleNamespace(**{k: getattr(p, k) for k in dir(p) if k.isupper()})
            pp.HEX_WEB = p.PRINT_HEX_WEB
            m.print_parts["grille"] = _cut_honeycomb(blank, (grille_a - 0.1, grille_r - 0.1), zg, pp)

    bezel = band(-p.GRILLE_RECESS, p.BEZEL_PROUD) & (
        front_outline(bezel_r - 0.1) - front_outline(grille_r)
    )
    bezel = _one_solid(bezel)
    # charcoal acoustic cloth behind the grille, so no red shows through the holes
    backing = None
    if p.GRILLE_BACKING == "paint":
        # matt black paint on the recess floor round the sound opening (render only)
        m.envelopes["grille_paint"] = band(-p.GRILLE_RECESS + 0.005, -p.GRILLE_RECESS + 0.03) & (
            front_outline(grille_r - 0.1) - _front_cyl(open_r, zg))
    elif p.GRILLE_BACKING == "cloth" and p.GRILLE_BACKING_THICK > 0:
        bt = p.GRILLE_BACKING_THICK
        body = body - (band(-p.GRILLE_RECESS - bt, -p.GRILLE_RECESS + 0.01) & front_outline(grille_r))
        backing = _one_solid(band(-p.GRILLE_RECESS - bt, -p.GRILLE_RECESS - 0.02)
                             & front_outline(grille_r - 0.1))

    if not visual_only:   # internals: skipped for quick previews
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
    knob_len = y_back - y_face
    knob = Pos(0, y_back, zk) * Rot(90, 0, 0) * Cylinder(kr, knob_len, align=MIN)
    knob = fillet(knob.edges().sort_by(Axis.Y)[0], min(1.0, knob_len / 4))  # rounded front edge
    # hidden boss on the back, sitting in a hole in the body wall, so a low
    # knob still gets enough grip on the encoder shaft
    boss_len = p.KNOB_BOSS_LENGTH
    knob = knob + Pos(0, y_back + boss_len, zk) * Rot(90, 0, 0) * Cylinder(
        p.KNOB_BOSS_DIA / 2, boss_len + 0.5, align=MIN)
    bore = knob_len + boss_len - p.KNOB_FACE_SKIN
    knob = knob - Pos(0, y_back + boss_len, zk) * Rot(90, 0, 0) * Cylinder(
        p.KNOB_SHAFT_DIA / 2, bore, align=MIN)                      # blind shaft bore
    knob = _one_solid(knob)
    body = _safe_cut(body, _front_cyl(p.KNOB_BOSS_DIA / 2 + p.FIT_CLEARANCE * 2, zk,
                                      depth=p.WALL + 2.4, y_from=-r_out(zk) + p.WALL + 1.2), "knob hole")
    body = _safe_cut(body, _front_cyl(p.LED_DIA / 2, z_led, depth=p.WALL + 2.4,
                                      y_from=-r_out(z_led) + p.WALL + 1.2), "LED hole")
    # light pipe in the LED hole (render only, not a separate part)
    m.envelopes["led"] = _front_cyl(p.LED_DIA / 2 - 0.05, z_led, depth=3,
                                    y_from=-r_out(z_led) + 3.2)
    I.update(z_knob=zk, z_led=z_led)

    # the collar port needs the solid (sealed) collar; radiator layouts use the body port
    usb_pos = p.USBC_POSITION if (p.USBC_POSITION != "collar" or no_pr) else "body"
    I["usbc_position"] = usb_pos
    # ---- USB-C port --------------------------------------------------------
    if usb_pos == "body":
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
        body = _safe_cut(body, port + pocket, "USB-C port")
        I.update(z_usbc=zu)

    # ---- nose cone ---------------------------------------------------------
    straight = math.atan2(rt, ch)
    a_base = straight + p.CONE_OGIVE * (a_top - straight)
    a_tip = math.radians(p.CONE_TIP_HALF_ANGLE_DEG)
    ztip = zt + ch
    if p.CONE_PROFILE_MODE == "points":
        # measured cone (fractions of cone height and base radius). The base
        # continues the body's slope (flush joint); the tip ends horizontal,
        # which gives the concept's soft, rounded point.
        cps = [(rt * rf, zt + tf * ch) for tf, rf in p.CONE_PROFILE_POINTS]
        cone_curve = Edge.make_spline(
            [_xz(r, z) for r, z in cps],
            tangents=[Vector(-math.sin(a_top), 0, math.cos(a_top)), Vector(-1, 0, -p.CONE_TIP_SOFTNESS)])
    else:
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
    foot_r = p.BODY_MAX_DIA * p.FOOT_DIA_FRAC / 2
    base_extra = {}
    if not base_pr and not no_pr:
        collar_h = z0 * p.COLLAR_HEIGHT_FRAC
        collar = Pos(0, 0, z0 - collar_h) * Solid.make_cone(
            rb * 0.9, rb, collar_h)                   # slight taper, flush with the body at the top
        stub = Pos(0, 0, p.FOOT_GROUND_GAP) * Cylinder(
            foot_r, z0 - collar_h - p.FOOT_GROUND_GAP + 0.5, align=MIN)
        foot = collar + stub
        if not closed_bottom:
            foot = foot + Pos(0, 0, z0 - 0.5) * Cylinder(
                r_open_bot - p.FIT_CLEARANCE, p.FOOT_SPIGOT_HEIGHT + 0.5, align=MIN)
    elif concept_base:
        # Concept base: slim tapered gold collar, a narrow vent gap under it
        # (reads as a dark shadow line, with a recessed dark mesh behind it), and a
        # small rounded gold foot. The radiator sits inside the body above the
        # bottom opening and breathes out through the collar bore and the gap.
        # With PR_POSITION = "none" there's no vent: the cup sits straight on the
        # foot and the collar is a solid plug that seals the bottom of the body.
        vg = p.BASE_VENT_GAP if base_vent else 0.0
        foot_h = p.FOOT_HEIGHT if no_pr else p.FOOT_HEIGHT - p.BASE_VENT_GAP
        g = p.FOOT_GROUND_GAP
        collar_h = z0 - g - foot_h - vg
        if collar_h < 3.0:
            raise ValueError("Not enough base clearance for foot + vent gap + collar")
        z_cb = z0 - collar_h
        z_ft = z_cb - vg                                       # top of the foot
        r_cb = p.BODY_MAX_DIA * p.COLLAR_BOTTOM_DIA_FRAC / 2

        def lathe(profile_edge, r_top, z_top, r_bot, z_bot):
            """Solid of revolution under a profile edge running top -> bottom."""
            edges = [Edge.make_line(_xz(0, z_top), _xz(r_top, z_top)), profile_edge]
            if r_bot > 1e-6:
                edges.append(Edge.make_line(_xz(r_bot, z_bot), _xz(0, z_bot)))
            edges.append(Edge.make_line(_xz(0, z_bot), _xz(0, z_top)))
            return _revolve_profile(edges)

        # gold cup: starts at the body's own slope, curves in and down so it
        # flows (across the vent line) into the foot
        down = lambda k: Vector(-k, 0, -1).normalized()
        cup = Edge.make_spline([_xz(rb, z0), _xz(r_cb, z_cb)],
                               tangents=[down(p.COLLAR_TOP_SLOPE), down(p.COLLAR_END_SLOPE)])
        collar = lathe(cup, rb, z0, r_cb, z_cb)
        spig_o = r_open_bot - p.FIT_CLEARANCE
        bore_top = spig_o - p.COLLAR_WALL
        bore_bot = r_cb - p.COLLAR_WALL - 1.0
        collar = collar + Pos(0, 0, z0 - 0.5) * Cylinder(spig_o, p.FOOT_SPIGOT_HEIGHT + 0.5, align=MIN)
        bore = Pos(0, 0, z_cb - 0.01) * Solid.make_cone(bore_bot, bore_top, collar_h + 0.02) + \
            Pos(0, 0, z0 - 1) * Cylinder(bore_top, p.FOOT_SPIGOT_HEIGHT + 2, align=MIN)
        foot = _one_solid(collar - bore) if base_vent else _one_solid(collar)
        # trims the fins to follow the cup (no step where they meet it)
        cup_clear = Edge.make_spline([_xz(rb + p.FIN_CUP_GAP, z0 + 0.01), _xz(r_cb + p.FIN_CUP_GAP, z_cb)],
                                     tangents=[down(p.COLLAR_TOP_SLOPE), down(p.COLLAR_END_SLOPE)])
        fin_clear = lathe(cup_clear, rb + p.FIN_CUP_GAP, z0 + 0.01, r_cb + p.FIN_CUP_GAP, z_cb) + \
            Pos(0, 0, -1) * Cylinder(r_cb + p.FIN_CUP_GAP, z_cb + 1.01, align=MIN)

        # small gold foot: a short cylinder with a rounded bottom edge (as in the concept)
        foot2 = Pos(0, 0, g) * Cylinder(foot_r, z_ft - g, align=MIN)
        try:
            foot2 = fillet(foot2.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[0],
                           min(p.FOOT_ROUND, foot_r - 0.5, (z_ft - g) - 0.5))
        except Exception:
            pass
        r_ft = foot_r
        base_extra = {"base_foot": _one_solid(foot2)}
        I.update(collar_bottom=z_cb, collar_top_dia=2 * rb, collar_bottom_dia=2 * r_cb,
                 foot_h=foot_h, foot_top=g + foot_h)
    if base_vent:
        # dark bronze vent insert, set deep: a plate on the foot top and a mesh ring
        r_mo = r_cb - p.BASE_VENT_RECESS                     # mesh outer radius
        r_mi = r_mo - p.BASE_VENT_MESH_THICK
        pl_t = p.BASE_VENT_PLATE
        # the dark plate covers the whole top of the foot, so every edge in the gap is dark
        vent = Pos(0, 0, z_ft - 0.01) * Cylinder(max(r_ft, r_mo), pl_t, align=MIN)
        vent = vent + Pos(0, 0, z_ft + pl_t - 0.2) * (
            Cylinder(r_mo, vg - pl_t + 0.4, align=MIN) - Cylinder(r_mi, vg + 1, align=MIN))
        vent = _one_solid(vent)
        base_extra["vent_insert"] = vent

        # flow path areas (report): radiator -> body opening -> collar bore -> mesh -> gap
        sd = math.pi * (p.PR_BASE_EFFECTIVE_DIA / 2) ** 2
        mesh_gross = 2 * math.pi * (r_mo + r_mi) / 2 * vg
        I.update(pr_sd=sd, collar_bottom=z_cb, collar_top_dia=2 * rb, collar_bottom_dia=2 * r_cb,
                 vent_gap=vg, vent_areas={
                     "body bottom opening": math.pi * bore_top ** 2,
                     "collar bore (narrowest)": math.pi * bore_bot ** 2,
                     "vent mesh (open area)": mesh_gross * p.BASE_VENT_MESH_OPEN,
                     "outer slot under the collar": 2 * math.pi * r_cb * vg},
                 pr_exit_area=min(math.pi * bore_bot ** 2, mesh_gross * p.BASE_VENT_MESH_OPEN,
                                  2 * math.pi * r_cb * vg),
                 foot_h=foot_h, foot_top=p.FOOT_GROUND_GAP + foot_h)
    elif base_pr:
        # collar = baffle for the down-firing radiator: a ring with a sound hole
        # and a thin locating spigot round the radiator frame
        collar_h = collar_h_ref
        z_cb = z0 - collar_h                                   # collar bottom
        collar = Pos(0, 0, z_cb) * Solid.make_cone(rb * 0.9, rb, collar_h)
        collar = collar - Pos(0, 0, z_cb - 1) * Cylinder(r_hole, collar_h + 2, align=MIN)
        spig_o = r_open_bot - p.FIT_CLEARANCE
        spig_i = p.PR_BASE_DIA / 2 + 0.2
        if spig_o - spig_i < 1.0:
            raise ValueError("Base radiator too big for the collar opening (spigot wall < 1 mm)")
        spigot = Pos(0, 0, z0 - 0.5) * (Cylinder(spig_o, p.FOOT_SPIGOT_HEIGHT + 0.5, align=MIN)
                                        - Cylinder(spig_i, p.FOOT_SPIGOT_HEIGHT + 2, align=MIN))
        foot = collar + spigot

        # stepped engine nozzle: injector plate (closes the ring) -> throat -> bell
        z_nt = z_cb - plenum                                   # nozzle top
        z_g = p.FOOT_GROUND_GAP
        exit_r = foot_r
        throat_r = exit_r * p.FOOT_NOZZLE_THROAT_FRAC
        nozzle = Pos(0, 0, z_nt - p.FOOT_NOZZLE_PLATE) * Cylinder(
            r_mesh_out + 0.3, p.FOOT_NOZZLE_PLATE, align=MIN)
        body_h_n = z_nt - p.FOOT_NOZZLE_PLATE - z_g            # throat + bell
        seg = body_h_n / (p.FOOT_NOZZLE_STEPS + 1)
        nozzle = nozzle + Pos(0, 0, z_nt - p.FOOT_NOZZLE_PLATE - seg) * Cylinder(
            throat_r, seg + 0.2, align=MIN)                    # throat
        # bell: each step is a short flared cone, wider at the bottom, so the
        # stack reads as a stepped rocket-engine bell
        prev_r = throat_r
        for k in range(p.FOOT_NOZZLE_STEPS):
            rk = throat_r + (exit_r - throat_r) * (k + 1) / p.FOOT_NOZZLE_STEPS
            zk = z_nt - p.FOOT_NOZZLE_PLATE - seg * (k + 2)
            top_r = prev_r + 0.35 * (rk - prev_r)
            nozzle = nozzle + Pos(0, 0, zk) * Solid.make_cone(rk, top_r, seg + 0.2)
            prev_r = rk
        # deflector cone inside the mesh ring: blocks the view through the mesh
        # and turns the airflow outward. Its tip stays thin at the collar hole
        # so the hole still passes the full radiator area.
        if p.BASE_DEFLECTOR:
            r_def = r_mesh_out - p.GRILLE_THICK - p.BASE_DEFLECTOR_GAP
            nozzle = nozzle + Pos(0, 0, z_nt - 0.2) * Solid.make_cone(r_def, 1.0, plenum - 0.3)
            I["deflector_base_dia"] = 2 * r_def
        nozzle = nozzle - Pos(0, 0, z_g - 1) * Cylinder(exit_r - 2.0, p.FOOT_NOZZLE_DISH + 1, align=MIN)
        nozzle = _one_solid(nozzle)
        try:
            nozzle = _one_solid(fillet(nozzle.edges().filter_by(GeomType.CIRCLE)
                                       .filter_by(lambda e: e.radius > exit_r - 0.1
                                                  and abs(e.center().Z - z_g) < 0.01), 0.8))
        except Exception:
            pass

        # perforated ring: same sheet and honeycomb as the front grille
        mesh = Pos(0, 0, z_nt - 0.3) * (Cylinder(r_mesh_out, plenum + 0.6, align=MIN)
                                        - Cylinder(r_mesh_out - p.GRILLE_THICK, plenum + 2, align=MIN))
        mesh = _one_solid(mesh)
        if p.HEX_PATTERN_ENABLED:
            mesh = _cut_honeycomb_ring(mesh, r_mesh_mid, z_nt + p.BASE_MESH_LAND,
                                       z_cb - p.BASE_MESH_LAND, p)
        if p.FOOT_POSTS:
            r_post = r_mesh_out - p.GRILLE_THICK - p.FOOT_POST_DIA / 2 - 1.0   # inside the mesh
            for k in range(p.FOOT_POSTS):
                d = _dir(p.FIN_ANGLE_OFFSET_DEG + k * 360 / p.FOOT_POSTS)
                nozzle = nozzle + Pos(d.X * r_post, d.Y * r_post, z_nt - 0.5) * Cylinder(
                    p.FOOT_POST_DIA / 2, plenum + 1.0, align=MIN)
        base_extra = {"nozzle": nozzle, "base_mesh": mesh}
        I.update(collar_bottom=z_cb, stub_top=z_nt, nozzle_exit_dia=2 * exit_r,
                 nozzle_throat_dia=2 * throat_r)
    if not base_vent:
        foot = _one_solid(fillet(foot.edges().sort_by(Axis.Z)[0], min(1.0, foot_r / 4)))
    if usb_pos == "collar":                         # after the fillet, which rebuilds the solid
        foot = _collar_usb_port(p, I, m, foot, cup, z0, z_cb)
    I.update(foot_dia=2 * foot_r, collar_h=collar_h, pr_position=p.PR_POSITION)
    if base_vent:
        # The radiator sits INSIDE the body on a flat moulded seat just above the
        # (small) bottom opening, and is fitted through the larger cone opening.
        r_pr = p.PR_BASE_DIA / 2
        z_seat = next(zz for zz in np.arange(z0, zt, 0.25) if r_in(zz) >= r_pr + 0.6)
        seat = (Pos(0, 0, z0) * Cylinder(r_pr + 2.0, z_seat - z0, align=MIN)
                - Pos(0, 0, z0 - 1) * Cylinder(r_open_bot, z_seat - z0 + 2, align=MIN)) \
            & offset_solid(-p.WALL + 0.3)
        if seat.volume > 1:
            body = body + seat
        battery_floor_z = z_seat + p.PR_BASE_DEPTH + p.PR_BACK_CLEARANCE
        I["z_pr_seat"] = z_seat
    elif base_pr:
        # battery/ballast sit above the radiator, leaving room for its back wave
        battery_floor_z = z0 + p.PR_BASE_DEPTH + p.PR_BACK_CLEARANCE

    # ---- fins --------------------------------------------------------------
    fins, tips = _build_fins(p, I, r_out, outer_solid, z0, bh, R, clear_r=rb, hollow=not visual_only,
                             clear_solid=fin_clear if concept_base else None)
    I["fin_tips"] = tips
    if usb_pos == "collar":
        # plug + cable fit: clearance to each fin and the foot knob, and the ground
        plug, cable = m.envelopes["usb_plug"], m.envelopes["usb_cable"]
        I.update(usbc_plug_fin_clear=min(plug.distance_to(f) for f in fins),
                 usbc_cable_fin_clear=min(cable.distance_to(f) for f in fins),
                 usbc_plug_knob_clear=plug.distance_to(base_extra["base_foot"]))
        ra_fit = {}
        for name, sol in m._usb_right_angle.items():
            ra_fit[name] = dict(
                fins=min(sol.distance_to(f) for f in fins),
                knob=sol.distance_to(base_extra["base_foot"]),
                ground=min(v.Z for v in sol.vertices()),
                collar=(lambda r: 0.0 if r is None else r.volume)(sol & foot),
                body=sol.distance_to(outer_solid))
        I["usbc_right_angle_fit"] = ra_fit

    fin_angles = [p.FIN_ANGLE_OFFSET_DEG + k * 360 / p.FIN_COUNT for k in range(p.FIN_COUNT)]
    rho = lambda key: p.MATERIAL_DENSITY[p.PART_MATERIALS[key]]

    def radial_cyl(radius, ang, z, r0, r1):
        """Cylinder pointing outward from the axis at angle ang, from radius r0 to r1."""
        return Rot(0, 0, ang - 90) * Pos(r0, 0, z) * Rot(0, 90, 0) * Cylinder(radius, r1 - r0, align=MIN)

    if not visual_only:   # internals: skipped for quick previews
        # ---- fins bolt through the body wall into the chassis rings ------------
        bolt_z = I["fin_bolt_z"]
        for ang in fin_angles:
            for zb in bolt_z:
                body = _safe_cut(body, radial_cyl(p.FIN_BOLT_CLEAR / 2, ang, zb, r_in(zb) - 3,
                                                  r_out(zb) + 1), "fin bolt hole")

    # ---- passive radiator ---------------------------------------------------
    rear_parts = {}
    if no_pr:
        pass                                            # sealed enclosure
    elif base_vent:
        m.envelopes["passive_radiator"] = Pos(0, 0, I["z_pr_seat"]) * Cylinder(
            p.PR_BASE_DIA / 2, p.PR_BASE_DEPTH, align=MIN)
        I.update(z_pr=I["z_pr_seat"] + p.PR_BASE_DEPTH / 2)
    elif base_pr:
        # down-firing, sitting on the collar (which is its baffle), inside the
        # bottom opening. It is part of the base module, fitted from below.
        m.envelopes["passive_radiator"] = Pos(0, 0, z0) * Cylinder(
            p.PR_BASE_DIA / 2, p.PR_BASE_DEPTH, align=MIN)
        I.update(z_pr=z0 + p.PR_BASE_DEPTH / 2)
    else:
        zp = z0 + bh * p.PR_Z_FRAC
        pr_rot = Rot(0, 0, p.PR_ANGLE_DEG - 180)          # built facing +Y (rear)

        def y_oval(w, h, y0, y1):
            return Pos(0, y1, zp) * extrude(Plane.XZ * Ellipse(w / 2, h / 2), amount=y1 - y0)

        ow, oh = p.PR_W / 2 + p.PR_RING_WIDTH, p.PR_H / 2 + p.PR_RING_WIDTH
        y_wall = []
        for th in np.linspace(0, 2 * math.pi, 72, endpoint=False):
            x, z = ow * math.cos(th), zp + oh * math.sin(th)
            ri = r_in(z)
            if ri > abs(x):
                y_wall.append(math.sqrt(ri * ri - x * x))
        y_pr = min(y_wall) - 0.5                           # flat seat, just inside the wall
        ow2, oh2 = p.PR_W - 2 * p.PR_FLANGE, p.PR_H - 2 * p.PR_FLANGE
        pr_seat = (y_oval(2 * ow, 2 * oh, y_pr, y_pr + 100) & offset_solid(-p.WALL + 0.3)) \
            - y_oval(ow2, oh2, y_pr - 5, y_pr + 100)
        body = body + pr_rot * pr_seat
        body = body - pr_rot * y_oval(ow2, oh2, y_pr - 5, r_out(zp) + 10)
        m.envelopes["passive_radiator"] = pr_rot * y_oval(p.PR_W, p.PR_H, y_pr - p.PR_DEPTH, y_pr)
        I.update(z_pr=zp)

        # ---- rear cover over the radiator (same design as the front grille) ------
        if p.REAR_COVER_ENABLED:
            cov_w, cov_h = ow2 + 2 * p.GRILLE_LEDGE, oh2 + 2 * p.GRILLE_LEDGE     # perforated sheet
            bez_w, bez_h = cov_w + 2 * p.BEZEL_WIDTH, cov_h + 2 * p.BEZEL_WIDTH   # bezel outline

            def rear_oval(w, h):
                return y_oval(w, h, 0, 200)

            body = body - pr_rot * (band(-p.GRILLE_RECESS, 5.0) & rear_oval(bez_w, bez_h))
            rg = _one_solid(band(-p.GRILLE_RECESS, -p.GRILLE_RECESS + p.GRILLE_THICK)
                            & rear_oval(cov_w - 0.2, cov_h - 0.2))
            if p.HEX_PATTERN_ENABLED:
                rg = _cut_honeycomb(rg, (cov_w / 2 - 0.1, cov_h / 2 - 0.1), zp, p)
            rbz = _one_solid(band(-p.GRILLE_RECESS, p.BEZEL_PROUD)
                             & (rear_oval(bez_w - 0.2, bez_h - 0.2) - rear_oval(cov_w, cov_h)))
            rear_parts = {"rear_grille": pr_rot * rg, "rear_bezel": pr_rot * rbz}
            I.update(rear_cover_size=(cov_w, cov_h), rear_bezel_size=(bez_w, bez_h))

    if not visual_only:   # internals: skipped for quick previews
        # ---- base module: ballast cup + battery ---------------------------------
        # Everything inside has to pass through an opening: the collar opening
        # (nose_tail), or the cone opening (nose). The foot, the ballast cup and the
        # battery go in together from below as one "base module". The ballast is a
        # steel sleeve round the upright battery, so the battery stays as low as it can.
        if p.SPLIT_MODE == "nose_tail":
            open_r = max(r_open_bot, inner[-1, 0])    # whichever end opening is bigger
        elif p.SPLIT_MODE == "nose":
            open_r = inner[-1, 0]
        else:
            open_r = R  # clamshell: the body opens fully
        I["insert_opening_dia"] = 2 * open_r
        batt, batt_info = _place_battery(p, r_in, battery_floor_z, zt,
                                         max_footprint=2 * (open_r - p.FIT_CLEARANCE))
        m.envelopes["battery"] = batt
        I.update(batt_info)
        bb = batt.bounding_box()

        r_bal = min(open_r, r_in(battery_floor_z)) - p.FIT_CLEARANCE - 0.5
        pocket_w, pocket_d = bb.size.X + 2 * p.BATTERY_CLEARANCE, bb.size.Y + 2 * p.BATTERY_CLEARANCE
        wire_slot = None
        if usb_pos == "collar":
            # USB-C wiring: a channel from the back of the port pocket up through the
            # collar spigot into the battery bay, then up a slot in the ballast cup
            # beside the battery to the PCB. The sealed receptacle keeps the air in.
            ud = _dir(p.USBC_ANGLE_DEG)
            sx, sy = (1 if ud.X >= 0 else -1), (1 if ud.Y >= 0 else -1)
            sw, sd = p.USBC_WIRE_SLOT
            if pocket_w >= pocket_d:        # slot in the long wall of the battery pocket
                xg, yg = sx * pocket_w / 4, sy * (pocket_d / 2 + sd / 2)
                slot_xy = (sw, sd + 0.02)
            else:
                xg, yg = sx * (pocket_w / 2 + sd / 2), sy * pocket_d / 4
                slot_xy = (sd + 0.02, sw)
            wire_slot = Pos(xg - sx * 0.01 * (pocket_w >= pocket_d), yg - sy * 0.01, 0) * Box(
                slot_xy[0], slot_xy[1], 1000, align=MIN)
            # leave the pocket straight out through its back face (square, no
            # grazing sliver), then turn up to the battery bay
            B0 = m._usb_pocket_back
            ax = m._usb_axis * -1.0                       # into the collar, along the port axis
            B1 = B0 + ax * 3.0
            G = Vector(xg, yg, battery_floor_z + 0.5)
            rw = p.USBC_WIRE_HOLE / 2
            chan = Location(Plane(origin=B0, z_dir=ax)) * Cylinder(rw, 3.0, align=MIN)
            chan = chan + Pos(B1.X, B1.Y, B1.Z) * Sphere(rw)
            C = Vector(G.X, G.Y, G.Z - 5.0)                # then up the last 5 mm vertically,
            chan = chan + Location(Plane(origin=B1, z_dir=(C - B1).normalized())) * \
                Cylinder(rw, (C - B1).length, align=MIN)   # so it exits the spigot top square
            chan = chan + Pos(C.X, C.Y, C.Z) * Sphere(rw)
            chan = chan + Pos(C.X, C.Y, C.Z) * Cylinder(rw, 6.0, align=MIN)
            L = 3.0 + (C - B1).length + 5.0
            foot = _safe_cut(foot, chan, "USB-C wire channel")
            I.update(usbc_wire_channel_len=L, usbc_wire_slot_xy=(xg, yg))
        t = p.CHASSIS_THICK
        g = -p.WALL - p.CHASSIS_GAP
        inside_ch = offset_solid(g)
        wall_plate = band(g - t, g)
        z_lo, z_hi = min(bolt_z) - 8, max(bolt_z) + 8

        # the cup may not rise above the underside of the driver (less a clearance)
        z_driver_bottom = zg - p.DRIVER_DIA / 2
        h_bal_max = max(0.0, z_driver_bottom - p.BALLAST_DRIVER_CLEARANCE - battery_floor_z)
        area_bal = math.pi * r_bal ** 2 - pocket_w * pocket_d
        if wire_slot is not None:
            area_bal -= p.USBC_WIRE_SLOT[0] * p.USBC_WIRE_SLOT[1]
        I.update(z_driver_bottom=z_driver_bottom,
                 ballast_max_g=h_bal_max * area_bal * rho("ballast") / 1000.0)

        def make_cup_and_chassis(ballast_g):
            """Ballast cup of the given mass round the battery, then the chassis:
            * 3 fin brackets: curved plates hugging the wall behind each fin. The fin
              bolts pass through the body into them, and a web + flange bolts each
              bracket to the ballast cup, so fin loads go into steel, not plastic.
            * a spine plate standing on the cup behind the driver, carrying the PCBs,
              with a tab under the driver magnet."""
            h_bal = ballast_g / rho("ballast") * 1000.0 / area_bal
            h_bal = min(h_bal, h_bal_max)       # can't grow into the driver
            cup, cup_top = None, battery_floor_z
            if h_bal > 0.1:
                cup = Pos(0, 0, battery_floor_z) * Cylinder(r_bal, h_bal, align=MIN)
                cup = _one_solid(cup - Pos(0, 0, battery_floor_z - 1) * Box(
                    pocket_w, pocket_d, h_bal + 2, align=MIN))
                if wire_slot is not None:
                    cup = _one_solid(cup - Pos(0, 0, battery_floor_z - 1) * wire_slot)
                cup_top = battery_floor_z + h_bal
            pieces = []
            for ang in fin_angles:
                r_mid = r_in((z_lo + z_hi) / 2)
                half = math.degrees(p.CHASSIS_BRACKET_WIDTH / 2 / r_mid)
                plate = wall_plate & _sector(ang - half, ang + half, z_lo, z_hi)
                # web, offset to one side of the bolt line so it clears the bolt heads
                web = Rot(0, 0, ang - 90) * Pos(r_bal + 0.3, p.CHASSIS_WEB_OFFSET, z_lo + 4) * Box(
                    100, t, z_hi - z_lo - 8, align=(Align.MIN, Align.CENTER, Align.MIN))
                flange = Rot(0, 0, ang - 90) * Pos(r_bal + 0.3, p.CHASSIS_WEB_OFFSET, z_lo + 4) * Box(
                    t, 14, z_hi - z_lo - 8, align=(Align.MIN, Align.CENTER, Align.MIN))
                br = (plate + (web & inside_ch) + flange)
                for zb in bolt_z:
                    br = br - radial_cyl(p.FIN_BOLT_CLEAR / 2, ang, zb, r_in(zb) - 10, r_out(zb) + 1)
                pieces.append(_one_solid(br))
            y_sp = I["y_driver_seat"] + p.DRIVER_DEPTH + 1.5         # just behind the driver magnet
            z_sp0 = max(cup_top, bb.max.Z) + 0.5
            z_sp1 = zt - p.CONE_SPIGOT_DEPTH - 5
            w_sp = 2 * r_bal                                          # fits through the opening
            spine = Pos(0, y_sp, z_sp0) * Box(w_sp, t, z_sp1 - z_sp0,
                                              align=(Align.CENTER, Align.MIN, Align.MIN))
            foot_fl = Pos(0, y_sp - 8, z_sp0) * Box(w_sp, 16 + t, t,
                                                    align=(Align.CENTER, Align.MIN, Align.MIN))
            z_tab = zg - p.DRIVER_DIA / 2 - 0.5
            y_tab0 = I["y_driver_seat"] + p.DRIVER_DEPTH * 0.4
            tab = Pos(0, y_tab0, z_tab - t) * Box(24, y_sp - y_tab0 + t, t,
                                                  align=(Align.CENTER, Align.MIN, Align.MIN))
            pieces.append(_one_solid((spine + foot_fl + tab) & inside_ch))
            chassis = None
            for sol in pieces:
                chassis = sol if chassis is None else chassis + sol
            info = dict(ballast_dia=2 * r_bal, ballast_h=h_bal, ballast_top=cup_top,
                        ballast_bottom=battery_floor_z, chassis_spine_y=y_sp, chassis_top=z_sp1,
                        chassis_pieces=len(pieces),
                        pcb_pos=(0.0, y_sp + t + 6.0, (z_sp0 + z_sp1) / 2),
                        # each bracket flange (z_lo+4 .. z_hi-4) must land fully on the cup
                        bracket_reaches_cup=(cup is not None and battery_floor_z <= z_lo + 4
                                             and cup_top >= z_hi - 4))
            return cup, chassis, info

        if p.BALLAST_MASS_G == "auto":
            # size the ballast so the total hits TARGET_MASS_G. Everything else is
            # already built except the chassis, whose spine length depends on the
            # cup height, so iterate a couple of times.
            def grams(shape, key):
                return shape.volume / 1000.0 * rho(key)
            pr_mass = 0.0 if no_pr else p.PR_BASE_MASS if base_pr else p.PR_MASS
            others = (grams(body, "body") + grams(cone, "nose_cone") + grams(foot, "foot")
                      + sum(grams(f, "fins") for f in fins) + grams(grille, "grille")
                      + grams(bezel, "bezel") + grams(knob, "knob")
                      + sum(grams(v, {"rear_grille": "grille", "rear_bezel": "bezel"}[k])
                            for k, v in rear_parts.items())
                      + sum(grams(v, {"nozzle": "foot", "base_mesh": "grille",
                                      "vent_insert": "vent_insert", "base_foot": "foot"}[k])
                            for k, v in base_extra.items())
                      + p.BATTERY_MASS + p.DRIVER_MASS + pr_mass + p.PCB_MASS + p.BUTYL_MASS_G
                      + (p.USBC_RECEPTACLE_MASS if usb_pos == "collar" else 0.0))
            ch_mass = 115.0
            for _ in range(4):
                ballast_g = max(0.0, p.TARGET_MASS_G - others - ch_mass)
                cup, chassis, cinfo = make_cup_and_chassis(ballast_g)
                new = grams(chassis, "chassis")
                if abs(new - ch_mass) < 0.2:
                    break
                ch_mass = new
        else:
            ballast_g = float(p.BALLAST_MASS_G)
            cup, chassis, cinfo = make_cup_and_chassis(ballast_g)
        ballast_g = min(ballast_g, I["ballast_max_g"])
        if cup is not None:
            m.parts["ballast"] = cup
            m.part_material_key["ballast"] = "ballast"
        m.parts["chassis"] = chassis
        m.part_material_key["chassis"] = "chassis"
        I.update(cinfo)
        I["ballast_mass"] = ballast_g

        # ---- fit checks between the internal items ------------------------------
        items = {"driver": m.envelopes["driver"], "battery": batt,
                 "chassis": m.parts["chassis"]}
        if "passive_radiator" in m.envelopes:
            items["passive radiator"] = m.envelopes["passive_radiator"]
        if "ballast" in m.parts:
            items["ballast"] = m.parts["ballast"]
        names = list(items)
        clashes = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                v = (items[names[i]] & items[names[j]]).volume
                clashes.append((names[i], names[j], v))
        I["clashes"] = clashes

    # ---- shadow line at the cone joint --------------------------------------
    body = _one_solid(body)
    if body.volume <= 0 or not body.is_valid:
        raise RuntimeError("Body solid is invalid/inside-out after the boolean steps")
    if p.JOINT_SHADOW_LINE > 0:
        body = _chamfer_rim(body, zt, rt, p.JOINT_SHADOW_LINE)
        cone = _chamfer_rim(cone, zt, rt, p.JOINT_SHADOW_LINE)

    # ---- split the body ----------------------------------------------------
    if p.SPLIT_MODE == "fin_clamshell":
        a0 = p.FIN_ANGLE_OFFSET_DEG
        wedge = _sector(-a0, a0, -10, H + 10)
        m.parts["body_front"] = _one_solid(body & wedge)
        m.parts["body_rear"] = _one_solid(body - wedge)
        m.part_material_key.update(body_front="body", body_rear="body")
    elif p.SPLIT_MODE in ("nose", "nose_tail"):
        m.parts["body"] = body
        m.part_material_key["body"] = "body"
    else:
        raise ValueError(f"Unknown SPLIT_MODE {p.SPLIT_MODE!r}")

    m.internal = {"chassis", "ballast"}
    parts_internal = {k: m.parts.pop(k) for k in ("ballast", "chassis") if k in m.parts}
    m.parts["nose_cone"] = cone
    for i, f in enumerate(fins):
        m.parts[f"fin_{i + 1}"] = f
        m.part_material_key[f"fin_{i + 1}"] = "fins"
    m.parts["foot"] = foot
    m.parts["grille"] = grille
    m.parts["bezel"] = bezel
    if backing is not None:
        m.parts["grille_backing"] = backing
        m.part_material_key["grille_backing"] = "grille_backing"
    m.parts["knob"] = knob
    for k, v in base_extra.items():
        m.parts[k] = v
        m.part_material_key[k] = {"nozzle": "foot", "base_mesh": "grille",
                                  "vent_insert": "vent_insert", "base_foot": "foot"}[k]
    if base_extra:
        m.parts["collar"] = m.parts.pop("foot")
        m.part_material_key["collar"] = "foot"
    if "base_foot" in m.parts:                   # vent style: the small rounded foot
        m.parts["foot"] = m.parts.pop("base_foot")
        m.part_material_key["foot"] = m.part_material_key.pop("base_foot")
    for k, v in rear_parts.items():
        m.parts[k] = v
        m.part_material_key[k] = {"rear_grille": "grille", "rear_bezel": "bezel"}[k]
    for k in ("nose_cone", "foot", "grille", "bezel", "knob"):
        if k in m.parts:
            m.part_material_key[k] = k
    m.parts.update(parts_internal)                      # internal parts last
    return m


def _sector(a0, a1, zlo, zhi):
    """A pie-slice prism around the axis between angles a0..a1 (0 = front)."""
    pts = [(0, 0)] + [(_dir(a).X * 400, _dir(a).Y * 400) for a in np.linspace(a0, a1, 9)]
    return Pos(0, 0, zlo) * extrude(Face(Wire(Polyline(*pts, close=True).edges())), amount=zhi - zlo)


def _chamfer_rim(solid, z, r, size):
    """Chamfer the outer circular edge at height z and radius r (the cone joint)."""
    edges = [e for e in solid.edges()
             if e.geom_type == GeomType.CIRCLE and abs(e.center().Z - z) < 0.01
             and abs(e.radius - r) < 0.05]
    if not edges:
        raise ValueError("Could not find the cone-joint edge to chamfer")
    return _one_solid(chamfer(edges, size))


# ---------------------------------------------------------------------------
# fins
# ---------------------------------------------------------------------------
def _bezier(p0, p1, p2, n=40):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2)


def _build_fins(p, I, r_out, outer_solid, z0, bh, R, clear_r=0.0, hollow=True, clear_solid=None):
    u_tip = p.FIN_TIP_REACH_FRAC * R
    z_rt = z0 + bh * p.FIN_ROOT_TOP_FRAC
    z_rb = z0 + bh * p.FIN_ROOT_BOTTOM_FRAC
    embed = 9.0  # start the outline inside the body, then trim flush
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
    r_ref = r_out(z_rt)
    # Fully rounded "cast" edges: first round the corners of the flat outline
    # (so the edge loop around the fin is smooth, with no sharp tip), then fillet
    # that loop on both faces. OpenCascade can't fillet sharp corners at this size.
    face = Face(outline)
    r2d = min(p.FIN_TIP_FLAT / 2 - 0.1, 6.0)
    try:
        face = fillet(face.vertices(), r2d)
    except Exception:
        pass
    slab = extrude(face, amount=(T0 + (T0 - T1)) / 2, both=True)
    # taper: intersect with a wedge that is T0 thick at the body and T1 at the tip
    # one straight taper (no crease): T0 where the fin leaves the body, T1 at the tip
    slope = (T0 - T1) / (u_tip - r_ref)
    ta, tb = T0 + slope * r_ref, T1 - slope
    wedge_pts = [(0, -ta / 2), (u_tip + 1, -tb / 2), (u_tip + 1, tb / 2), (0, ta / 2)]
    wedge = Pos(0, 0, -5) * extrude(Face(Wire(Polyline(*wedge_pts, close=True).edges())),
                                    amount=z_rt + 20)
    blank = _one_solid(slab & wedge)
    I["fin_fillet_used"] = 0.0
    rmax = min(p.FIN_EDGE_FILLET, T1 / 2 - 0.2)
    for rad in (rmax, rmax * 0.9, rmax * 0.8, rmax * 0.65, rmax * 0.5):
        try:
            # every edge except those buried in the body (trimmed off anyway)
            edges = [e for e in blank.edges() if e.center().X > r_ref - embed + 2]
            blank = _one_solid(fillet(edges, rad))
            I["fin_fillet_used"] = rad
            break
        except Exception:
            continue
    if p.FIN_TOP_TAPER > 0:
        # thin the top end of the fin to a point so it blends into the body. The
        # taper curve leaves the flat faces tangentially, so there's no crease.
        zt0 = z_rt - p.FIN_TOP_TAPER
        h1, h2 = T1 / 2, p.FIN_TOP_THICK / 2

        def side(sg):
            return Edge.make_spline([Vector(0, sg * h1, zt0), Vector(0, sg * h2, z_rt + 1)],
                                    tangents=[Vector(0, 0, 1), Vector(0, -sg * 0.35, 1).normalized()])
        big = ta + 2
        prof = Wire([
            Edge.make_line(Vector(0, -big, -30), Vector(0, big, -30)),
            Edge.make_line(Vector(0, big, -30), Vector(0, big, zt0)),
            Edge.make_line(Vector(0, big, zt0), Vector(0, h1, zt0)),
            side(1),
            Edge.make_line(Vector(0, h2, z_rt + 1), Vector(0, h2, z_rt + 40)),
            Edge.make_line(Vector(0, h2, z_rt + 40), Vector(0, -h2, z_rt + 40)),
            Edge.make_line(Vector(0, -h2, z_rt + 40), Vector(0, -h2, z_rt + 1)),
            side(-1).reversed(),
            Edge.make_line(Vector(0, -h1, zt0), Vector(0, -big, zt0)),
            Edge.make_line(Vector(0, -big, zt0), Vector(0, -big, -30)),
        ])
        taper = Pos(-150, 0, 0) * extrude(Face(prof), amount=300, dir=(1, 0, 0))
        blank = _one_solid(blank & taper)
    I["fin_solid_volume"] = _one_solid(blank - outer_solid).volume

    # bolt positions along the root
    bolt_z = [z_rb + f * (z_rt - z_rb) for f in p.FIN_BOLTS_Z_FRAC]
    I["fin_bolt_z"] = bolt_z

    def along_x(radius, x0, x1, z):
        return Pos(x0, 0, z) * Rot(0, 90, 0) * Cylinder(radius, x1 - x0, align=MIN)

    solid_blank = blank                                   # kept for the 3D-printed prototype
    if hollow and p.FIN_WALL > 0:
        # Hollow it like a die-casting: a core FIN_WALL in from every outside
        # surface, open on the root side against the body. Cast bosses inside
        # take the M4 bolts that come through the body from the chassis.
        w = p.FIN_WALL
        core2d = offset(face, amount=-w, kind=Kind.ARC).faces()[0]
        min_core = 1.5                                   # stop where the core gets too thin
        u_lim = (ta - 2 * w - min_core) / slope if slope > 1e-9 else u_tip + 1
        cav_pts = [(0, -(ta - 2 * w) / 2), (u_lim, -min_core / 2),
                   (u_lim, min_core / 2), (0, (ta - 2 * w) / 2)]
        cav_wedge = Pos(0, 0, -5) * extrude(
            Face(Wire(Polyline(*cav_pts, close=True).edges())), amount=z_rt + 20)
        cavity = extrude(core2d, amount=ta, both=True) & cav_wedge
        if p.FIN_TOP_TAPER > 0:                              # no core in the thin tapered top
            cavity = cavity & Pos(0, 0, -50) * Box(400, 400, z_rt - p.FIN_TOP_TAPER + 50, align=MIN)
        for zb in bolt_z:
            ro = r_out(zb)
            cavity = cavity - along_x(p.FIN_BOSS_DIA / 2, ro - 4, ro + p.FIN_BOSS_LENGTH, zb)
        blank = blank - cavity
    for zb in bolt_z:
        ro = r_out(zb)
        pilot = along_x(p.FIN_BOLT_PILOT / 2, ro - 6, ro + p.FIN_BOSS_LENGTH - 4, zb)  # blind
        blank = blank - pilot
        solid_blank = solid_blank - pilot
    # keep clear of the collar under the body
    under = clear_solid if clear_solid is not None else (
        Pos(0, 0, -1) * Cylinder(clear_r + 1.0, z0 + 1.0, align=MIN) if clear_r else None)
    blank = _one_solid(blank - outer_solid - under if under else blank - outer_solid)
    solid_blank = _one_solid(solid_blank - outer_solid - under if under else solid_blank - outer_solid)
    I["fin_taper_half_deg"] = math.degrees(math.atan(slope / 2))
    foot_pad = blank & Box(400, 400, 0.6, align=MIN)
    u_c = foot_pad.center().X  # centre of the ground contact patch

    fins, tips = [], []
    n = p.FIN_COUNT
    for k in range(n):
        ang = p.FIN_ANGLE_OFFSET_DEG + k * 360 / n
        fins.append(Rot(0, 0, ang - 90) * copy.deepcopy(blank))  # own copy so STEP keeps separate names
        I.setdefault("fins_solid", []).append(Rot(0, 0, ang - 90) * copy.deepcopy(solid_blank))
        d = _dir(ang)
        tips.append((d.X * u_c, d.Y * u_c))
    I.update(fin_tip_reach=u_tip, z_fin_root_top=z_rt, z_fin_root_bottom=z_rb)
    return fins, tips


# ---------------------------------------------------------------------------
# battery
# ---------------------------------------------------------------------------
def _place_battery(p, r_in, z_floor, z_top, max_footprint=1e9):
    """Try the battery box in each orientation; keep the one whose centre is
    lowest. Orientations whose footprint can't pass through the assembly
    opening (max_footprint) are skipped, so the battery can actually be fitted."""
    L, W, T = p.BATTERY_SIZE
    best = None
    for (h, a, b) in ((T, L, W), (W, L, T), (L, W, T)):
        if math.hypot(a, b) > max_footprint:
            continue
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
def _hex_ring_counts(r_mid, band_h, p):
    """Holes around a cylinder of mid-radius r_mid, and rows in a band of height band_h."""
    pitch = p.HEX_HOLE + p.HEX_WEB
    n_around = int(2 * math.pi * r_mid // pitch)
    hex_r = p.HEX_HOLE / math.sqrt(3)
    rows = int((band_h - 2 * hex_r) // (pitch * math.sqrt(3) / 2)) + 1 if band_h > 2 * hex_r else 0
    return n_around, rows


def _cut_honeycomb_ring(ring, r_mid, z_lo, z_hi, p):
    """Punch the grille's honeycomb radially through a cylindrical band between
    z_lo and z_hi (pointy-top hexagons, alternate rows offset by half a pitch)."""
    from build123d import RegularPolygon, Compound
    pitch = p.HEX_HOLE + p.HEX_WEB
    hex_r = p.HEX_HOLE / math.sqrt(3)
    n_around, rows = _hex_ring_counts(r_mid, z_hi - z_lo, p)
    dz = pitch * math.sqrt(3) / 2
    used = (rows - 1) * dz
    z_start = (z_lo + z_hi) / 2 - used / 2
    base = extrude(Plane.YZ * RegularPolygon(hex_r, 6, major_radius=True, rotation=30),
                   amount=6, both=True)
    tools = []
    for j in range(rows):
        off = 0.5 if j % 2 else 0.0
        for i in range(n_around):
            ang = (i + off) * 360.0 / n_around
            tools.append(Rot(0, 0, ang) * Pos(r_mid, 0, z_start + j * dz) * base)
    return _one_solid(ring - Compound(tools))


def _cut_honeycomb(grille, radius, zg, p):
    """Punch a hexagonal hole pattern through a (curved) grille, along Y.
    radius is a number (round grille) or (half-width, half-height) for an oval.
    Holes are pointy-top hexagons, so they also print cleanly in an upright part."""
    from build123d import RegularPolygon, Compound
    a, b = (radius, radius) if np.isscalar(radius) else radius
    pitch = p.HEX_HOLE + p.HEX_WEB
    dx = pitch
    dz = pitch * math.sqrt(3) / 2
    hex_r = p.HEX_HOLE / math.sqrt(3)       # circumradius from across-flats
    m_ = p.HEX_WEB + hex_r                  # keep a solid border
    la, lb = a - m_, b - m_
    tools = []
    base = extrude(Plane.XZ * RegularPolygon(hex_r, 6, major_radius=True, rotation=30), amount=120, both=True)
    j = 0
    z = -lb
    while z <= lb + 1e-6:
        off = (dx / 2) if (j % 2) else 0.0
        x = -la - off
        while x <= la + 1e-6:
            if (x / la) ** 2 + (z / lb) ** 2 <= 1.0:
                tools.append(Pos(x, 0, zg + z) * base)
            x += dx
        z += dz
        j += 1
    return _one_solid(grille - Compound(tools))
