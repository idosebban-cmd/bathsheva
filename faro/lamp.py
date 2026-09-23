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
    GeomType,
    Plane,
    Pos,
    RectangleRounded,
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
    cavity = Pos(0, 0, p.BASE_FLOOR) * Cylinder(rb - p.BASE_WALL, hb - p.BASE_FLOOR - p.BASE_WALL, align=MIN)
    base = base - cavity
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
        letters = Pos(0, 0, zn) * _front_prism(Text(p.NAMEPLATE_TEXT, p.NAMEPLATE_TEXT_H))
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
    m.envelopes["battery"] = Pos(0, -4, p.BASE_FLOOR + 0.5) * Box(bl, bw, bt, align=MIN)
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

    # arched windows on the front, each with a frosted diffuser behind it
    ww, wh = p.WINDOW_W, p.WINDOW_H

    def arch(wd, ht):
        """Arched window outline (round top) in the XZ plane, centred on its middle."""
        rr = wd / 2
        rect = Pos(0, -(ht / 2) + (ht - rr) / 2) * Rectangle(wd, ht - rr)
        top = Pos(0, ht / 2 - rr) * Circle(rr)
        return (rect + top).faces()[0] if len((rect + top).faces()) == 1 else rect + top

    diffusers = []
    for i, zw in enumerate(p.WINDOW_Z):
        zw = z_(zw)
        opening = Pos(0, 0, zw) * _front_prism(arch(ww, wh), depth=200)
        tower = tower - opening
        ri = r_out(zw) - w
        band = _revolve([(ri - p.DIFFUSER_THICK, zw - 30), (ri - 0.02, zw - 30),
                         (ri - 0.02, zw + 30), (ri - p.DIFFUSER_THICK, zw + 30)])
        m_ = p.DIFFUSER_MARGIN
        diff = band & Pos(0, 0, zw) * _front_prism(arch(ww + 2 * m_, wh + 2 * m_), depth=200)
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
    ring = lambda za: Pos(0, 0, za) * (Cylinder(rl, hr, align=MIN) - Cylinder(rl - 3.0, hr + 1, align=MIN))
    frame = ring(z_l0) + ring(z_l1 - hr)
    for k in range(p.MULLIONS):
        ang = (k + 0.5) * 360 / p.MULLIONS            # a panel (not a mullion) faces the front
        frame = frame + Rot(0, 0, ang) * Pos(0, -(rl - p.MULLION_DEPTH / 2), z_l0) * Box(
            p.MULLION_W, p.MULLION_DEPTH, z_l1 - z_l0, align=MIN)
    m.parts["lantern_frame"] = _one(frame)
    rgl = rl - p.MULLION_DEPTH - 0.1
    glass = Pos(0, 0, z_l0 + hr) * (Cylinder(rgl, z_l1 - z_l0 - 2 * hr, align=MIN)
                                    - Cylinder(rgl - p.GLASS_THICK, z_l1 - z_l0, align=MIN))
    m.parts["lantern_glass"] = _one(glass)
    m.envelopes["led"] = Pos(0, 0, (z_l0 + z_l1) / 2 - p.LED_H / 2) * Cylinder(p.LED_DIA / 2, p.LED_H, align=MIN)

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
    cap = rim + dome + boss
    m.parts["cap"] = _one(cap)
    rf = p.FINIAL_DIA / 2
    z_top = p.OVERALL_HEIGHT
    finial = Pos(0, 0, z_top - rf) * Sphere(rf) + Pos(0, 0, z_d1 + p.CAP_BOSS_H - 1.0) * Cylinder(
        rf * 0.45, z_top - rf - (z_d1 + p.CAP_BOSS_H - 1.0), align=MIN)
    m.parts["finial"] = _one(finial)
    I.update(z_gallery=(z_g0, z_g1), z_lantern=(z_l0, z_l1), z_cap_top=z_d1, H=z_top)
    return m
