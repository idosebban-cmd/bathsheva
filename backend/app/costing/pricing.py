"""Retail price -> target factory cost per sales channel, and pass / close / fail. Pure."""

from __future__ import annotations

from typing import Any

PRICING_KEYS = ["retail_price", "retail_low", "retail_high", "premium_retail", "vat_rate", "dtc_factory_share",
                "retailer_margin", "wholesale_factory_share", "close_band"]


def factory_targets(retail_inc_vat: float, p: dict[str, float]) -> dict[str, float]:
    """Target factory cost for one retail price (inc. VAT)."""
    ex_vat = retail_inc_vat / (1 + p["vat_rate"])
    wholesale = ex_vat * (1 - p["retailer_margin"])
    return {
        "retail_inc_vat": retail_inc_vat,
        "retail_ex_vat": round(ex_vat, 2),
        "wholesale": round(wholesale, 2),
        "dtc": round(ex_vat * p["dtc_factory_share"], 2),
        "retail": round(wholesale * p["wholesale_factory_share"], 2),
    }


def targets(p: dict[str, float]) -> dict[str, Any]:
    """Targets at the planned retail price, its range, and the premium edition price."""
    mid = factory_targets(p["retail_price"], p)
    lo = factory_targets(p["retail_low"], p)
    hi = factory_targets(p["retail_high"], p)
    return {
        "standard": mid,
        "bands": {
            "dtc": {"target": mid["dtc"], "low": lo["dtc"], "high": hi["dtc"]},
            "retail": {"target": mid["retail"], "low": lo["retail"], "high": hi["retail"]},
        },
        "premium": factory_targets(p["premium_retail"], p),
    }


def status(cost: float, target: float, close_band: float) -> str:
    """pass: at or under target; close: within close_band above it; fail: further above."""
    if cost <= target:
        return "pass"
    if cost <= target * (1 + close_band):
        return "close"
    return "fail"


def assess(cost_mid: float, t: dict[str, float], close_band: float) -> dict[str, Any]:
    """Status against both channel targets, with the gap in GBP (positive = over target)."""
    return {
        ch: {"target": t[ch], "status": status(cost_mid, t[ch], close_band), "gap": round(cost_mid - t[ch], 2)}
        for ch in ("dtc", "retail")
    }
