"""
Faro lighthouse lamp geometry (build123d).

    import params as p, lamp
    m = lamp.build(p)          # m.parts: name -> solid, m.envelopes: placeholders

Every round form is a solid of revolution about Z (like Atelier's body). The
front (-Y) carries the windows, knob and nameplate; the USB-C port is on the
rear (+Y) of the walnut base.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from build123d import (
    Align,
    Axis,
    Box,
    Circle,
    Cylinder,
    Edge,
    Face,
    FontStyle,
    GeomType,
    Plane,
    Pos,
    RectangleRounded,
    RegularPolygon,
    Rectangle,
    Rot,
    SlotOverall,
    Sphere,
    Text,
    Torus,
    Vector,
    Wire,
    extrude,
    fillet,
    revolve,
)

MIN = (Align.CENTER, Align.CENTER, Align.MIN)


@dataclass
class Lamp:
    parts: dict = field(default_factory=dict)
    envelopes: dict = field(default_factory=dict)   # placeholders (not printed)
    info: dict = field(default_factory=dict)


def _xz(r, z):
    return Vector(r, 0, z)


def _revolve(points):
    """Closed (r, z) polygon in the XZ plane, spun about Z."""
    return revolve(Face(Wire.make_polygon([_xz(r, z) for r, z in points], close=True)), Axis.Z, 360)


def _one(shape):
    sols = shape.solids()
    return sols[0] if len(sols) == 1 else max(sols, key=lambda s: s.volume)


def _front_prism(face_on_xz, depth=400.0):
    """A sketch drawn in the XZ plane (as seen from the front), pushed along -Y."""
    return extrude(Plane.XZ * face_on_xz, amount=depth)


def _dir(angle_deg):
    """Unit vector in XY at an angle from the front (-Y), as in Atelier."""
    a = math.radians(angle_deg)
    return Vector(math.sin(a), -math.cos(a), 0)


def _sector_box(half_deg, r, z0, h):
    """A wedge from the axis spanning +-half_deg about the front (-Y), z0..z0+h."""
    a = math.radians(half_deg)
    pts = [(0, 0), (r * math.sin(-a), -r * math.cos(a)), (0, -r * 1.05), (r * math.sin(a), -r * math.cos(a))]
    from build123d import Polygon
    return Pos(0, 0, z0) * extrude(Polygon(*pts, align=None), amount=h)


def _safe_fillet(shape, edges, r):
    try:
        return fillet(edges, r)
    except Exception:
        return shape


def build(p) -> Lamp:
    m = Lamp()
    I = m.info
    S = p.OVERALL_HEIGHT / p.REF_HEIGHT          # scales the main forms
    z_ = lambda v: v * S
    d_ = lambda v: v * S

    # ---- 1. walnut base --------------------------------------------------
    rb, hb = d_(p.BASE_DIA) / 2, z_(p.BASE_H)
    base = Cylinder(rb, hb, align=MIN)
    base = _safe_fillet(base, base.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1:], p.BASE_TOP_ROUND)
    base = _safe_fillet(base, base.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[:1], p.BASE_BOTTOM_ROUND)
    # open ring: a rebate at the bottom for the plate, the battery bay above it,
    # and a hole through the top for the wires up the tower
    pt = p.PLATE_THICK
    r_reb = rb - p.PLATE_REBATE
    r_cav = rb - p.BASE_WALL
    z_cav_top = hb - p.BASE_TOP_WALL
    base = base - Pos(0, 0, -1) * Cylinder(r_reb, pt + 1, align=MIN)
    base = base - Pos(0, 0, pt - 0.01) * Cylinder(r_cav, z_cav_top - pt + 0.01, align=MIN)
    base = base - Pos(0, 0, z_cav_top - 1) * Cylinder(p.BASE_WIRE_HOLE / 2, p.BASE_TOP_WALL + 2, align=MIN)
    # screw bosses hanging from the top of the bay, with holes for M3 inserts
    screw_xy = []
    for k in range(p.SCREWS):
        d = _dir(p.SCREW_ANGLE0 + k * 360 / p.SCREWS)
        x, y = d.X * p.SCREW_R, d.Y * p.SCREW_R
        screw_xy.append((x, y))
        base = base + Pos(x, y, pt) * Cylinder(p.BOSS_DIA / 2, z_cav_top - pt + 0.5, align=MIN)
        base = base - Pos(x, y, pt - 0.01) * Cylinder(p.BOSS_PILOT_DIA / 2, 10.0, align=MIN)

    # bottom plate: flush in the rebate, 4 countersunk screws, 4 magnet pockets,
    # and a shallow recess underneath for the felt pad
    rp = r_reb - p.PLATE_CLEAR
    plate_b = Cylinder(rp, pt, align=MIN)
    r_felt = rp - p.FELT_INSET
    plate_b = plate_b - Pos(0, 0, -1) * Cylinder(r_felt + 0.3, p.FELT_RECESS + 1, align=MIN)
    z_f = p.FELT_RECESS                                   # recess floor
    screws = None
    for x, y in screw_xy:
        plate_b = plate_b - Pos(x, y, -1) * Cylinder(p.SCREW_CLEAR_DIA / 2, pt + 2, align=MIN)
        cs = (p.SCREW_HEAD_DIA - p.SCREW_CLEAR_DIA) / 2          # 90 deg countersink depth
        sink = Pos(x, y, z_f - 0.01) * _revolve([(0, 0), (p.SCREW_HEAD_DIA / 2, 0),
                                                 (p.SCREW_CLEAR_DIA / 2, cs), (0, cs)])
        plate_b = plate_b - sink
        head = Pos(x, y, z_f + 0.05) * _revolve([(0, 0), (p.SCREW_HEAD_DIA / 2 - 0.1, 0),
                                                 (p.SCREW_CLEAR_DIA / 2 - 0.2, cs - 0.1), (0, cs - 0.1)])
        shank = Pos(x, y, z_f + cs - 0.2) * Cylinder(p.SCREW_CLEAR_DIA / 2 - 0.2, 8.0, align=MIN)
        head = head - Pos(x, y, z_f - 0.5) * extrude(RegularPolygon(0.8 / math.cos(math.pi / 6), 6), amount=1.8)
        screws = head + shank if screws is None else screws + head + shank
    mags = None
    for k in range(p.MAGNETS):
        d = _dir(p.SCREW_ANGLE0 + (k + 0.5) * 360 / p.MAGNETS)
        x, y = d.X * p.SCREW_R, d.Y * p.SCREW_R
        plate_b = plate_b - Pos(x, y, z_f - 0.01) * Cylinder(p.MAGNET_DIA / 2 + 0.1, p.MAGNET_THICK + 0.1, align=MIN)
        mg = Pos(x, y, z_f) * Cylinder(p.MAGNET_DIA / 2, p.MAGNET_THICK, align=MIN)
        mags = mg if mags is None else mags + mg
    m.parts["base_plate"] = _one(plate_b)
    felt = Pos(0, 0, z_f - p.FELT_THICK) * Cylinder(r_felt, p.FELT_THICK, align=MIN)
    m.parts["felt_pad"] = felt
    m.envelopes["screws"] = screws
    m.envelopes["magnets"] = mags
    lift = p.FELT_THICK - p.FELT_RECESS                   # the felt stands proud; it's the foot
    I.update(felt_proud=lift, battery_bay=(2 * r_cav, z_cav_top - pt),
             plate_dia=2 * rp, felt_dia=2 * r_felt)

    # nameplate: a curved brass plate in a shallow recess on the front
    zn = z_(p.NAMEPLATE_Z)
    plate_outline = Pos(0, 0, zn) * _front_prism(RectangleRounded(p.NAMEPLATE_W, p.NAMEPLATE_H, 1.2))
    shell = lambda r0, r1: Cylinder(r1, hb, align=MIN) - Cylinder(r0, hb + 1, align=MIN)
    recess = shell(rb - p.NAMEPLATE_RECESS, rb + 2) & plate_outline
    base = base - recess
    r_plate_out = rb - p.NAMEPLATE_RECESS + p.NAMEPLATE_THICK
    plate = shell(rb - p.NAMEPLATE_RECESS + 0.01, r_plate_out) & Pos(0, 0, zn) * _front_prism(
        RectangleRounded(p.NAMEPLATE_W - 0.2, p.NAMEPLATE_H - 0.2, 1.1))
    try:
        letters = Pos(0, 0, zn) * _front_prism(Text(p.NAMEPLATE_TEXT, p.NAMEPLATE_TEXT_H, font_style=FontStyle.BOLD))
        plate = plate + (shell(r_plate_out - 0.05, r_plate_out + p.NAMEPLATE_TEXT_RAISE) & letters)
        I["nameplate_text"] = True
    except Exception as e:                         # no font available: plain plate
        I["nameplate_text"] = f"skipped ({e})"
    # USB-C port, low on the rear
    port = Pos(0, 0, p.USBC_Z) * extrude(Plane.XZ * SlotOverall(p.USBC_W, p.USBC_H), amount=-rb - 5)
    base = base - port
    m.envelopes["usb_receptacle"] = Pos(0, rb - p.BASE_WALL - 4.0, p.USBC_Z) * Box(
        9.5, 7.5, 3.6, align=(Align.CENTER, Align.MIN, Align.CENTER))
    bl, bw, bt = p.BATTERY_SIZE
    m.envelopes["battery"] = Pos(0, -4, pt + 0.5) * Box(bl, bw, bt, align=MIN)
    # the battery must fit the bay, clear the bosses, and come out past them
    bat = m.envelopes["battery"]
    I["battery_clear"] = dict(bay_height_margin=z_cav_top - pt - 0.5 - bt,
                              boss_clash=sum((bat & (Pos(x, y, 0) * Cylinder(p.BOSS_DIA / 2, hb, align=MIN))).volume
                                             if (bat & (Pos(x, y, 0) * Cylinder(p.BOSS_DIA / 2, hb, align=MIN))) is not None
                                             else 0.0 for x, y in screw_xy))
    m.parts["base"] = _one(base)
    m.parts["nameplate"] = plate
    I.update(base_dia=2 * rb, base_h=hb)

    # ---- 2. cream band ----------------------------------------------------
    z_cb0, z_cb1 = hb, hb + z_(p.CREAM_BAND_H)
    rc = d_(p.CREAM_BAND_DIA) / 2
    band_c = Pos(0, 0, z_cb0) * Cylinder(rc, z_cb1 - z_cb0, align=MIN)
    band_c = _safe_fillet(band_c, band_c.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1:],
                          p.CREAM_BAND_ROUND)
    band_c = band_c - Pos(0, 0, z_cb0 - 1) * Cylinder(rc - 8.0, z_cb1 - z_cb0 + 2, align=MIN)
    m.parts["band_cream"] = _one(band_c)

    # ---- 3. tower cone (red band = its lower part) ------------------------
    z_t0, z_red, z_t1 = z_cb1, z_(p.RED_BAND_TOP_Z), z_(p.TOWER_TOP_Z)
    r0, r1 = d_(p.TOWER_BOTTOM_DIA) / 2, d_(p.TOWER_TOP_DIA) / 2
    r_out = lambda z: r0 + (r1 - r0) * (z - z_t0) / (z_t1 - z_t0)
    w = p.SHELL_WALL
    cone_shell = lambda za, zb: _revolve([(r_out(za) - w, za), (r_out(za), za), (r_out(zb), zb),
                                          (r_out(zb) - w, zb)])
    red = cone_shell(z_t0, z_red)
    tower = cone_shell(z_red, z_t1)

    # arched windows spiralling up the tower, each with a frosted diffuser behind it
    ww, wh = p.WINDOW_W, p.WINDOW_H

    def arch(wd, ht):
        """Arched window outline (round top) in the XZ plane, centred on its middle."""
        rr = wd / 2
        rect = Pos(0, -(ht / 2) + (ht - rr) / 2) * Rectangle(wd, ht - rr)
        top = Pos(0, ht / 2 - rr) * Circle(rr)
        return (rect + top).faces()[0] if len((rect + top).faces()) == 1 else rect + top

    diffusers = []
    n_w = p.WINDOWS
    win = []
    for i in range(n_w):
        f = i / (n_w - 1) if n_w > 1 else 0.0
        win.append((p.WINDOW_Z_FIRST + f * (p.WINDOW_Z_LAST - p.WINDOW_Z_FIRST), i * p.WINDOW_TURN_DEG))
    I["windows"] = [(round(z_(z), 1), a % 360) for z, a in win]
    for i, (zw, ang) in enumerate(win):
        zw = z_(zw)
        turn = Rot(0, 0, ang)                         # the front (-Y) prism turned to this window
        opening = turn * Pos(0, 0, zw) * _front_prism(arch(ww, wh), depth=200)
        tower = tower - opening
        # a thin conical skin that follows the tower's inner wall
        ri = lambda z: r_out(z) - w
        za, zb = zw - 30, zw + 30
        band = _revolve([(ri(za) - p.DIFFUSER_THICK, za), (ri(za) - 0.02, za),
                         (ri(zb) - 0.02, zb), (ri(zb) - p.DIFFUSER_THICK, zb)])
        m_ = p.DIFFUSER_MARGIN
        diff = band & turn * Pos(0, 0, zw) * _front_prism(arch(ww + 2 * m_, wh + 2 * m_), depth=200)
        diffusers.append(_one(diff))
    m.parts["band_red"] = _one(red)
    m.parts["tower"] = _one(tower)
    for i, dfz in enumerate(diffusers):
        m.parts[f"window_diffuser_{i + 1}"] = dfz

    # brass dimmer knob on the front of the red band
    zk = z_(p.KNOB_Z)
    rk = p.KNOB_DIA / 2
    y_surf = -r_out(zk)
    knob = Pos(0, y_surf + 1.0, zk) * Rot(90, 0, 0) * Cylinder(rk, p.KNOB_PROUD + 1.0, align=MIN)
    knob = _safe_fillet(knob, knob.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Y)[:1], 1.0)
    m.parts["knob"] = knob
    I.update(z_red_top=z_red, z_tower_top=z_t1, z_knob=zk)

    # ---- 4. brass gallery: platform ring + railing --------------------------
    rg = d_(p.GALLERY_DIA) / 2
    z_g0, z_g1 = z_t1, z_t1 + z_(p.GALLERY_THICK)
    rl = d_(p.LANTERN_DIA) / 2
    gal = Pos(0, 0, z_g0) * Cylinder(rg, z_g1 - z_g0, align=MIN)
    gal = _safe_fillet(gal, gal.edges().filter_by(GeomType.CIRCLE), p.GALLERY_ROUND)
    gal = gal - Pos(0, 0, z_g0 - 1) * Cylinder(rl - 4.0, z_g1 - z_g0 + 2, align=MIN)
    rr_ = d_(p.RAIL_DIA) / 2 - p.RAIL_POST_DIA / 2
    rh = z_(p.RAIL_H)
    for k in range(p.RAIL_POSTS):
        d = _dir(k * 360 / p.RAIL_POSTS + 180 / p.RAIL_POSTS)
        gal = gal + Pos(d.X * rr_, d.Y * rr_, z_g1 - 0.5) * Cylinder(p.RAIL_POST_DIA / 2, rh + 0.5, align=MIN)
    for zr in (z_g1 + rh - p.RAIL_BAR_DIA / 2, z_g1 + rh * p.RAIL_MID_FRAC):
        gal = gal + Pos(0, 0, zr) * Torus(rr_, p.RAIL_BAR_DIA / 2)
    m.parts["gallery"] = _one(gal)

    # ---- 5. lantern: brass frame + frosted glass ----------------------------
    z_l0, z_l1 = z_g1, z_(p.LANTERN_TOP_Z)
    hr = p.LANTERN_RING_H
    tb, lip = p.TOP_BAND_H, p.LIP_H
    r_lip = rl - 3.0                                   # lip inner radius (the opening under the cap)
    z_tb = z_l1 - tb                                   # bottom of the top band
    ann = lambda ro, ri, za, h: Pos(0, 0, za) * (Cylinder(ro, h, align=MIN) - Cylinder(ri, h + 2, align=MIN))
    # the glass stands on the gallery and the frame is lowered over it, so the
    # bottom ring must clear the glass
    rgl = rl - p.MULLION_DEPTH - 0.1                   # glass outer radius (inside the mullions)
    frame = ann(rl, rgl + p.FIT_CLEAR, z_l0, hr)                      # bottom ring
    frame = frame + ann(rl, p.GROOVE_R, z_tb, tb)                     # top band: outer skin...
    frame = frame + ann(p.GROOVE_R + 0.01, r_lip, z_l1 - lip, lip)    # ...and the bayonet lip
    # entry slots through the lip, midway between mullions, and a stop under the
    # lip LOCK_TURN_DEG further round (the lug turns until it hits it)
    lug_half = math.degrees(p.LOCK_LUG_W / 2 / r_lip)
    slot_w = p.LOCK_LUG_W + 2 * p.FIT_CLEAR
    for k in range(p.LOCK_LUGS):
        a0 = k * 360 / p.LOCK_LUGS
        # the slot is a true ring segment through the lip only (a box overran the curved
        # lip and nicked the outer band, leaving knife-edge slivers)
        half = math.degrees(slot_w / 2 / r_lip)
        seg = Pos(0, 0, z_l1 - lip - 0.5) * (Cylinder(p.GROOVE_R, lip + 1.0, align=MIN)
                                             - Cylinder(r_lip - 0.5, lip + 1.0, align=MIN))
        frame = frame - (seg & Rot(0, 0, a0) * _sector_box(half, p.GROOVE_R + 5, z_l1 - lip - 1, lip + 2))
        sgn = 1 if p.LOCK_TURN_DEG >= 0 else -1
        a_stop = a0 + p.LOCK_TURN_DEG + sgn * (lug_half + math.degrees(1.0 / r_lip))
        frame = frame + Rot(0, 0, a_stop) * Pos(0, -(p.GROOVE_R + r_lip) / 2, z_tb) * Box(
            1.5, p.GROOVE_R - r_lip + 0.2, tb - lip + 0.2, align=MIN)
    for k in range(p.MULLIONS):
        ang = (k + 0.5) * 360 / p.MULLIONS            # a panel (not a mullion) faces the front
        frame = frame + Rot(0, 0, ang) * Pos(0, -(rl - p.MULLION_DEPTH / 2), z_l0) * Box(
            p.MULLION_W, p.MULLION_DEPTH, z_tb - z_l0 + 0.5, align=MIN)
    m.parts["lantern_frame"] = _one(frame)
    glass = Pos(0, 0, z_l0) * (Cylinder(rgl, z_tb - z_l0, align=MIN)
                                    - Cylinder(rgl - p.GLASS_THICK, z_l1 - z_l0, align=MIN))
    m.parts["lantern_glass"] = _one(glass)
    m.envelopes["led"] = Pos(0, 0, (z_l0 + z_tb) / 2 - p.LED_H / 2) * Cylinder(p.LED_DIA / 2, p.LED_H, align=MIN)
    I.update(led_access_dia=2 * r_lip,
             glass_frame_clash=(lambda r_: 0.0 if r_ is None else r_.volume)(glass & m.parts["lantern_frame"]),
             glass_on_gallery=(lambda r_: 0.0 if r_ is None else r_.volume)(glass & m.parts["gallery"]))

    # ---- 6. red cap + brass finial -------------------------------------------
    rcr = d_(p.CAP_RIM_DIA) / 2
    hcr = z_(p.CAP_RIM_H)
    rim = Pos(0, 0, z_l1) * Cylinder(rcr, hcr, align=MIN)
    rim = _safe_fillet(rim, rim.edges().filter_by(GeomType.CIRCLE), min(2.0, hcr / 2 - 0.1))
    rd = d_(p.CAP_DOME_DIA) / 2
    z_d0, z_d1 = z_l1 + hcr - 0.5, z_(p.CAP_TOP_Z)
    dome_curve = Edge.make_spline([_xz(rd, z_d0), _xz(0, z_d1)],
                                  tangents=[Vector(0, 0, 1), Vector(-1, 0, 0)])
    dome = revolve(Face(Wire([Edge.make_line(_xz(0, z_d0), _xz(rd, z_d0)), dome_curve,
                              Edge.make_line(_xz(0, z_d1), _xz(0, z_d0))])), Axis.Z, 360)
    # short flared collar on top of the dome, under the finial
    rbo = p.CAP_BOSS_DIA / 2
    boss = _revolve([(0, z_d1 - 2.0), (rbo, z_d1 - 2.0), (rbo, z_d1 - 0.5),
                     (rbo * 0.6, z_d1 + p.CAP_BOSS_H), (0, z_d1 + p.CAP_BOSS_H)])
    # bayonet spigot under the cap: a tube that fits inside the lip, with lugs at
    # its foot that pass the slots and lock under the lip
    r_sp = r_lip - p.FIT_CLEAR
    z_lug_top = z_l1 - lip - p.FIT_CLEAR
    z_sp0 = z_lug_top - p.LOCK_LUG_H
    spigot = ann(r_sp, r_sp - p.SPIGOT_WALL, z_sp0, z_l1 - z_sp0 + 0.5)

    def lugs(turn):
        out = None
        for k in range(p.LOCK_LUGS):
            lg = Rot(0, 0, k * 360 / p.LOCK_LUGS + turn) * Pos(0, -(r_sp - 0.2), z_sp0) * Box(
                p.LOCK_LUG_W, p.GROOVE_R - p.FIT_CLEAR - (r_sp - 0.2), p.LOCK_LUG_H,
                align=(Align.CENTER, Align.MAX, Align.MIN))
            out = lg if out is None else out + lg
        return out
    cap = rim + dome + boss + spigot + lugs(p.LOCK_TURN_DEG)          # modelled locked
    m.parts["cap"] = _one(cap)
    # fit checks: locked (no clash with the frame, lugs under the lip) and at the
    # entry angle (lugs pass through the slots)
    clash = lambda a_, b_: 0.0 if (a_ & b_) is None else (a_ & b_).volume
    I["bayonet"] = dict(
        locked_clash=clash(m.parts["cap"], m.parts["lantern_frame"]),
        entry_clash=clash(lugs(0.0), m.parts["lantern_frame"]),
        lug_overlap_under_lip=(p.GROOVE_R - p.FIT_CLEAR) - r_lip,
        led_passes=p.LED_DIA < 2 * (r_sp - p.SPIGOT_WALL))
    rf = p.FINIAL_DIA / 2
    z_top = p.OVERALL_HEIGHT
    finial = Pos(0, 0, z_top - rf) * Sphere(rf) + Pos(0, 0, z_d1 + p.CAP_BOSS_H - 1.0) * Cylinder(
        rf * 0.45, z_top - rf - (z_d1 + p.CAP_BOSS_H - 1.0), align=MIN)
    m.parts["finial"] = _one(finial)
    I.update(z_gallery=(z_g0, z_g1), z_lantern=(z_l0, z_l1), z_cap_top=z_d1)
    # everything was built with the walnut's underside at z = 0; the felt stands
    # proud of it, so lift the lot to put the felt on the ground
    lift = I["felt_proud"]
    for dct in (m.parts, m.envelopes):
        for k_ in list(dct):
            if dct[k_] is not None:
                dct[k_] = Pos(0, 0, lift) * dct[k_]
    I["H"] = z_top + lift
    return m
