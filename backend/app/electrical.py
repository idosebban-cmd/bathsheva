"""Battery runtime estimate from the battery spec and the LED loads. Pure (no DB).

    runtime_h = cells x capacity (Ah) x cell voltage x usable fraction x driver efficiency
                / sum of the loads at full brightness (W)
"""

from __future__ import annotations

from typing import Any

# A runtime within this fraction below the target counts as "close" rather than "fail".
CLOSE_BAND = 0.10


def battery_energy_wh(battery: dict[str, Any]) -> float:
    return float(battery["cells"]) * float(battery["cell_capacity_mah"]) / 1000 * float(battery["cell_voltage"])


def estimate(spec: dict[str, Any], target_h: float | None = None, removed_parts: set[str] | None = None) -> dict[str, Any]:
    """Runtime at full brightness with every light on, and per load on its own."""
    removed = removed_parts or set()
    bat = spec["battery"]
    eff = float(spec["driver_efficiency"])
    energy = battery_energy_wh(bat)
    delivered = energy * float(bat["usable_fraction"]) * eff
    loads = [ld for ld in spec.get("loads", []) if ld.get("part") not in removed]
    watts = sum(float(ld["watts"]) for ld in loads)
    hours = delivered / watts if watts > 0 else None
    status = "unknown"
    if hours is not None and target_h:
        status = "pass" if hours >= target_h else ("close" if hours >= target_h * (1 - CLOSE_BAND) else "fail")
    unverified = not bat.get("verified", False) or any(not ld.get("verified", False) for ld in loads)
    return {
        "hours": round(hours, 1) if hours is not None else None,
        "target_h": target_h,
        "status": status,
        "battery_wh": round(energy, 1),
        "delivered_wh": round(delivered, 1),
        "load_w": round(watts, 2),
        "loads": [{"part": ld.get("part"), "name": ld["name"], "watts": float(ld["watts"]),
                   "hours_alone": round(delivered / float(ld["watts"]), 1) if float(ld["watts"]) > 0 else None,
                   "source": ld.get("source", "model-generated"), "verified": bool(ld.get("verified", False))}
                  for ld in loads],
        "assumptions": {
            "cells": bat["cells"], "cell_capacity_mah": bat["cell_capacity_mah"], "cell_voltage": bat["cell_voltage"],
            "usable_fraction": bat["usable_fraction"], "driver_efficiency": eff,
            "source": bat.get("source", "model-generated"), "confidence": bat.get("confidence", "low"),
        },
        "unverified": unverified,
        "note": "Full brightness, all lights on, a new battery at room temperature. Dimmed use runs much longer; "
                "capacity falls with age and cold. Confirm with the chosen cells and driver.",
    }
