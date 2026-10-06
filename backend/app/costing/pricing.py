"""Retail price -> target factory cost per sales channel, and pass / close / fail. Pure."""

from __future__ import annotations

from typing import Any

PRICING_KEYS = ["retail_price", "retail_low", "retail_high", "premium_retail", "vat_rate", "dtc_factory_share",
                "retailer_margin", "wholesale_factory_share", "close_band"]
STACK_KEYS = ["stack_freight", "stack_delivery", "stack_payment_pct", "stack_payment_fixed", "stack_returns_pct",
              "stack_marketing", "stack_one_off", "stack_profit_pct"]
PRICING_KEYS += STACK_KEYS
STACK_PCT_KEYS = ["stack_payment_pct", "stack_returns_pct", "stack_profit_pct"]


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


def _required_ex_vat(per_unit: float, p: dict[str, float], profit: float) -> float:
    """Ex-VAT price at which per-unit costs plus the percentage lines (and profit) are covered."""
    pct = p["stack_returns_pct"] + p["stack_payment_pct"] * (1 + p["vat_rate"]) + profit
    if pct >= 1:
        raise ValueError("Percentage lines add up to 100% or more of the price")
    return per_unit / (1 - pct)


def stack_lines(factory_cost: float, quantity: float, retail_inc_vat: float, p: dict[str, float]) -> list[dict[str, Any]]:
    """DTC price stack at one retail price: where each pound of the price goes (GBP per lamp)."""
    ex = retail_inc_vat / (1 + p["vat_rate"])
    lines = [
        ("vat", "VAT", retail_inc_vat - ex),
        ("factory", "Factory cost (landed, incl. certification share)", factory_cost),
        ("freight", "Inbound handling and storage", p["stack_freight"]),
        ("delivery", "Delivery to customer", p["stack_delivery"]),
        ("payment", "Payment fees", retail_inc_vat * p["stack_payment_pct"] + p["stack_payment_fixed"]),
        ("returns", "Returns and warranty", ex * p["stack_returns_pct"]),
        ("marketing", "Marketing per sale", p["stack_marketing"]),
        ("one_off", "One-off launch costs (shared)", p["stack_one_off"] / quantity),
    ]
    used = sum(v for _, _, v in lines)
    lines.append(("profit", "Profit", retail_inc_vat - used))
    return [{"key": k, "label": lbl, "amount": round(v, 2)} for k, lbl, v in lines]


def price_stack(factory_cost: float, quantity: float, p: dict[str, float]) -> dict[str, Any]:
    """Break-even retail price and the retail price for the profit target (both inc. VAT) for one factory cost."""
    per_unit = (factory_cost + p["stack_freight"] + p["stack_delivery"] + p["stack_payment_fixed"]
                + p["stack_marketing"] + p["stack_one_off"] / quantity)
    vat = 1 + p["vat_rate"]
    be = _required_ex_vat(per_unit, p, 0.0) * vat
    tgt = _required_ex_vat(per_unit, p, p["stack_profit_pct"]) * vat
    planned = p.get("retail_price") or 0.0
    out = {
        "factory_cost": round(factory_cost, 2), "quantity": quantity,
        "break_even_retail": round(be, 2), "target_retail": round(tgt, 2),
        "lines": stack_lines(factory_cost, quantity, tgt, p),
    }
    if planned:
        at_planned = stack_lines(factory_cost, quantity, planned, p)
        profit = at_planned[-1]["amount"]
        out["at_planned"] = {"retail": planned, "profit": profit,
                             "profit_pct": round(profit / (planned / vat), 4)}
    return out
