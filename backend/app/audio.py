"""Speaker acoustics and power from the template's audio spec and the CAD box volume. Pure (no DB, no CAD).

First-order estimates to check the specification is plausible and to brief suppliers; they never replace
measurements. Driver and radiator Thiele-Small values in the template are placeholders until the supplier's
datasheet arrives, so every result is flagged unverified.

* Box alignment (closed-box equivalent): alpha = Vas / Vb, fc = Fs x sqrt(1 + alpha), Qtc = Qts x sqrt(1 + alpha).
* Passive radiator: the moving mass that tunes it to fb in the box, Mmp = rho c^2 Sp^2 / (Vb (2 pi fb)^2), ignoring
  its own suspension (the supplier adds that).
* Loudness: the amplifier-limited (thermal) SPL is sensitivity + 10 log10(P). The excursion-limited SPL of a piston
  of area S moving x (peak) at f, on a table (half space) at r = 1 m, is p = rho S x (2 pi f)^2 / (2 pi r).
* Battery: peak input power = amplifier RMS / (amplifier efficiency x boost efficiency); peak current at the cells'
  loaded voltage, shared by the parallel cells.
* Charging: charge power = min(USB-C PD power x charger efficiency, cells x max charge rate x capacity x 4.2 V);
  time = energy / charge power x CV factor (the slow constant-voltage finish).
"""

from __future__ import annotations

import math
from typing import Any

RHO = 1.2  # air, kg/m³
RHO_C2 = 1.42e5  # rho c², Pa
P_REF = 20e-6  # Pa


def _spl(p_peak: float) -> float:
    return 20 * math.log10(p_peak / math.sqrt(2) / P_REF)


def excursion_spl(area_cm2: float, xmax_mm: float, f_hz: float, r_m: float = 1.0) -> float:
    """Highest SPL (dB, half space) a piston can make at f without passing xmax."""
    p = RHO * area_cm2 * 1e-4 * xmax_mm * 1e-3 * (2 * math.pi * f_hz) ** 2 / (2 * math.pi * r_m)
    return _spl(p)


def evaluate(audio: dict[str, Any], box_l: float, battery: dict[str, Any] | None = None) -> dict[str, Any]:
    drv, pr, amp = audio["driver"], audio["passive_radiator"], audio["amplifier"]
    alpha = float(drv["vas_l"]) / box_l
    fc = float(drv["fs_hz"]) * math.sqrt(1 + alpha)
    qtc = float(drv["qts"]) * math.sqrt(1 + alpha)
    fb = float(pr["target_fb_hz"])
    sp = float(pr["sd_cm2"]) * 1e-4
    mmp_g = RHO_C2 * sp**2 / (box_l * 1e-3 * (2 * math.pi * fb) ** 2) * 1000
    p_amp = float(amp["rms_w"])
    thermal = float(drv["sensitivity_db"]) + 10 * math.log10(min(p_amp, float(drv["power_rms_w"])))
    target_spl = float(audio.get("target_spl_db", 90))
    f_low = float(audio.get("target_low_hz", 60))
    bass = []
    for f in sorted({f_low, fb, 100.0, 150.0, 200.0}):
        d = excursion_spl(float(drv["sd_cm2"]), float(drv["xmax_mm"]), f)
        r = excursion_spl(float(pr["sd_cm2"]), float(pr["xmax_mm"]), f) if f <= 1.5 * fb else None
        bass.append({"f_hz": round(f), "driver_db": round(d, 1), "radiator_db": None if r is None else round(r, 1)})
    # lowest frequency at which the driver alone reaches the target SPL within xmax (SPL rises 12 dB/octave)
    d_low = excursion_spl(float(drv["sd_cm2"]), float(drv["xmax_mm"]), 100.0)
    f_full = 100.0 * 10 ** ((target_spl - d_low) / 40)
    out: dict[str, Any] = {
        "full_spl_from_hz": round(f_full),
        "box_l": round(box_l, 3),
        "alpha": round(alpha, 2), "fc_hz": round(fc), "qtc": round(qtc, 2),
        "pr_target_fb_hz": round(fb), "pr_moving_mass_g": round(mmp_g, 1),
        "thermal_spl_db": round(thermal, 1), "target_spl_db": target_spl,
        "spl_ok": thermal >= target_spl, "driver_power_ok": float(drv["power_rms_w"]) >= p_amp,
        "bass": bass, "target_low_hz": f_low,
        "unverified": not all(x.get("verified", False) for x in (drv, pr, amp)),
    }
    if battery:
        cells = int(battery["cells"])
        p_in = p_amp / (float(amp["efficiency"]) * float(amp["boost_efficiency"]))
        v_loaded = float(amp.get("cell_loaded_voltage", 3.2))
        i_total = p_in / v_loaded
        i_cell = i_total / cells  # 1S2P: the cells share the current
        ch = audio["charging"]
        cap_ah = float(battery["cell_capacity_mah"]) / 1000
        energy_wh = cells * cap_ah * float(battery["cell_voltage"])
        p_charge = min(float(ch["pd_w"]) * float(ch["charger_efficiency"]), cells * float(ch["max_charge_c"]) * cap_ah * 4.2)
        hours = energy_wh / p_charge * float(ch["cv_factor"])
        out.update({
            "peak_input_w": round(p_in, 1), "peak_current_a": round(i_total, 1), "peak_cell_current_a": round(i_cell, 1),
            "cell_max_a": float(amp["cell_max_continuous_a"]), "current_ok": i_cell <= float(amp["cell_max_continuous_a"]),
            "charge_power_w": round(p_charge, 1), "charge_h": round(hours, 1),
            "charge_target_h": float(ch["target_h"]), "charge_ok": hours <= float(ch["target_h"]),
        })
    return out
