"""
Numbers for the report: internal air volume, mass, centre of mass, tip-over angle.
"""
from __future__ import annotations

import math

import numpy as np
from build123d import CenterOf, Vector


def air_volume(model):
    """Air inside the sealed body: the inner cavity minus everything that
    sits in it (spigots, driver mount, driver and battery envelopes)."""
    air = model.envelopes["body_cavity"]
    for name, part in model.parts.items():
        air = air - part
    air = air - model.envelopes["driver"] - model.envelopes["battery"]
    body_l = air.volume / 1e6
    cone_l = model.info["cone_cavity_volume"] / 1e6
    return body_l, cone_l


def mass_properties(model, p):
    """Per-part mass and the overall centre of mass (CoM)."""
    rows = []
    total_m = 0.0
    moment = np.zeros(3)
    for name, part in model.parts.items():
        mat = p.PART_MATERIALS[model.part_material_key[name]]
        rho = p.MATERIAL_DENSITY[mat]
        vol_cm3 = part.volume / 1000.0
        mass = vol_cm3 * rho
        c = part.center(CenterOf.MASS)
        rows.append(dict(name=name, material=mat, volume_cm3=vol_cm3, mass_g=mass, com_z=c.Z))
        total_m += mass
        moment += mass * np.array([c.X, c.Y, c.Z])

    I = model.info
    drv = model.envelopes["driver"].center(CenterOf.MASS)
    bat = model.envelopes["battery"].center(CenterOf.MASS)
    bat_top = bat.Z + (bat.Z - I["battery_z_bottom"])
    pcb = Vector(0, 0, bat_top + p.PCB_ABOVE_BATTERY)
    for name, mass, c in (("battery (bought-in)", p.BATTERY_MASS, bat),
                          ("driver (bought-in)", p.DRIVER_MASS, drv),
                          ("PCB (bought-in)", p.PCB_MASS, pcb)):
        rows.append(dict(name=name, material="-", volume_cm3=None, mass_g=mass, com_z=c.Z))
        total_m += mass
        moment += mass * np.array([c.X, c.Y, c.Z])
    com = moment / total_m
    return rows, total_m, com


def tip_angles(model, com):
    """Tilt angle at which the CoM passes over each edge of the support triangle.

    The rocket stands only on its fin tips, so the support area is the triangle
    joining them. Tilting it about one edge lifts the CoM; once the CoM is
    directly above that edge it falls over. The angle is
    atan(horizontal distance from CoM to edge / CoM height)."""
    tips = model.info["fin_tips"]
    cx, cy, cz = com
    res = []
    n = len(tips)
    for i in range(n):
        (x1, y1), (x2, y2) = tips[i], tips[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        d = abs(ex * (cy - y1) - ey * (cx - x1)) / math.hypot(ex, ey)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        direction = math.degrees(math.atan2(mx, -my)) % 360  # 0 = front, 90 = right
        res.append(dict(edge=(i, (i + 1) % n), dist=d,
                        angle=math.degrees(math.atan2(d, cz)), direction_deg=direction))
    return sorted(res, key=lambda r: r["angle"])


def overall_dims(model):
    from build123d import Compound
    bb = Compound(list(model.parts.values())).bounding_box()
    return bb
