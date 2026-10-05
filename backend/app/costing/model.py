"""Unit cost model (SPEC §8). Pure: inputs in, numbers out; no database access.

Every input is a named `Assumption` with a low/high range and provenance. The
cost is a function of those values and the production quantity Q:

  per part (x quantity per product):
    material   = mass bought (kg) x price (GBP/kg)
    process    = cycle minutes x machine rate / 60
    setup      = setup hours x machine rate / Q          (one batch per run)
    finishing  = max(minimum charge, visible area x rate)
  per part design:
    tooling    = tooling cost / Q
  product level:
    bought-in items, assembly (minutes x labour rate), packaging

Ranges: each input's low/high is first widened by its confidence (low-confidence
inputs get the widest ranges). The estimate is the cost at every input's
midpoint; the range moves each input to its widened low and high in turn and
combines those effects as independent uncertainties (root-sum-square), so it is
not the unlikely case of every input at its worst at once. That all-worst-case
envelope is reported separately as `worst_low` / `worst_high`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

CATEGORY_ORDER = ["material", "process", "setup", "finishing", "tooling", "bought_in", "assembly", "packaging"]


@dataclass(frozen=True)
class Assumption:
    key: str
    label: str
    unit: str
    low: float
    high: float
    confidence: str = "low"  # low | medium | high
    verified: bool = False
    source: str = "model-generated"
    group: str = ""  # e.g. "Material prices", "Machine rates"

    def widened(self, spread: dict[str, float]) -> tuple[float, float]:
        w = 0.0 if self.verified else spread.get(self.confidence, 0.25)
        return max(self.low * (1 - w), 0.0), self.high * (1 + w)

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2


@dataclass
class PartGeometry:
    volume_mm3: float
    size_mm: tuple[float, float, float]  # bounding box x, y, z
    axisymmetric: bool = True

    @property
    def volume_cm3(self) -> float:
        return self.volume_mm3 / 1000

    @property
    def outer_diameter_mm(self) -> float:
        return max(self.size_mm[0], self.size_mm[1])

    @property
    def visible_area_m2(self) -> float:
        """Outer side + top area, used for finishing (m2)."""
        x, y, z = self.size_mm
        if self.axisymmetric:
            d = max(x, y)
            area = math.pi * d * z + math.pi * (d / 2) ** 2
        else:
            area = 2 * (x + y) * z + x * y
        return area / 1e6

    def cnc_stock_cm3(self, allowance_mm: float) -> float:
        x, y, z = self.size_mm
        if self.axisymmetric:
            d = max(x, y) + allowance_mm
            vol = math.pi / 4 * d * d * (z + allowance_mm)
        else:
            vol = (x + allowance_mm) * (y + allowance_mm) * (z + allowance_mm)
        return vol / 1000


@dataclass
class PartSpec:
    """One manufactured part and which assumption keys drive its cost."""

    part_id: int
    name: str
    quantity: int  # per product
    process_key: str
    process_name: str
    material_key: str
    material_name: str
    density_g_cm3: float
    geometry: PartGeometry
    finish_key: str | None
    finish_name: str | None
    basis: str  # "decided" | "recommended"
    cnc_allowance_mm: float | None = None  # set when the process is CNC (stock-based material)
    tooling_band: str = "none"


@dataclass
class ItemSpec:
    """A product-level line: bought-in component, assembly or packaging."""

    item_id: int
    kind: str  # bought_in | assembly | packaging | other
    name: str
    quantity: float
    unit: str  # pcs | min
    cost_key: str  # assumption key for GBP per unit (or labour rate for minutes)
    qty_key: str | None = None  # assumption key when the quantity itself is an assumption (minutes)


@dataclass
class CostInputs:
    assumptions: dict[str, Assumption]
    parts: list[PartSpec] = field(default_factory=list)
    items: list[ItemSpec] = field(default_factory=list)
    spread: dict[str, float] = field(default_factory=lambda: {"high": 0.0, "medium": 0.10, "low": 0.25})

    # Keys used by each part / item, filled in by `keys_for_part`.
    def keys_for_part(self, p: PartSpec) -> dict[str, str]:
        k = {
            "price": f"mat_price:{p.material_key}",
            "rate": f"rate:{p.process_key}",
            "setup": f"setup:{p.process_key}",
            "cycle": f"cycle:{p.process_key}",
            "cycle_kg": f"cycle_kg:{p.process_key}",
            "util": f"util:{p.process_key}",
            "tooling": f"tooling:{p.part_id}",
        }
        if p.cnc_allowance_mm is not None:
            k["removal"] = f"removal:{p.process_key}"
        if p.finish_key:
            k["finish_m2"] = f"finish_m2:{p.finish_key}"
            k["finish_min"] = f"finish_min:{p.finish_key}"
        return k

    def mids(self) -> dict[str, float]:
        return {k: a.mid for k, a in self.assumptions.items()}

    def lows(self) -> dict[str, float]:
        return {k: a.widened(self.spread)[0] for k, a in self.assumptions.items()}

    def highs(self) -> dict[str, float]:
        return {k: a.widened(self.spread)[1] for k, a in self.assumptions.items()}


@dataclass
class Line:
    category: str
    part_id: int | None
    item_id: int | None
    label: str
    amount: float
    keys: list[str]


def part_quantities(p: PartSpec, keys: dict[str, str], v: dict[str, float]) -> dict[str, float]:
    finished_kg = p.geometry.volume_cm3 * p.density_g_cm3 / 1000
    if p.cnc_allowance_mm is not None:
        stock_cm3 = p.geometry.cnc_stock_cm3(p.cnc_allowance_mm)
        bought_kg = stock_cm3 * p.density_g_cm3 / 1000
        removed = max(stock_cm3 - p.geometry.volume_cm3, 0.0)
        minutes = v[keys["cycle"]] + removed * v[keys["removal"]]
    else:
        bought_kg = finished_kg * v[keys["util"]]
        removed = 0.0
        minutes = v[keys["cycle"]] + finished_kg * v[keys["cycle_kg"]]
    return {"finished_kg": finished_kg, "bought_kg": bought_kg, "removed_cm3": removed, "minutes": minutes}


def evaluate(inputs: CostInputs, values: dict[str, float], quantity: float) -> list[Line]:
    """Cost lines per product at production quantity Q, for one set of assumption values."""
    q = max(float(quantity), 1.0)
    lines: list[Line] = []
    for p in inputs.parts:
        k = inputs.keys_for_part(p)
        n = p.quantity
        qty = part_quantities(p, k, values)
        rate = values[k["rate"]]
        lines.append(Line("material", p.part_id, None, p.name, n * qty["bought_kg"] * values[k["price"]], [k["price"]] + (
            [k["util"]] if p.cnc_allowance_mm is None else [])))
        lines.append(Line("process", p.part_id, None, p.name, n * qty["minutes"] * rate / 60,
                          [k["rate"], k["cycle"]] + ([k["removal"]] if "removal" in k else [k["cycle_kg"]])))
        lines.append(Line("setup", p.part_id, None, p.name, values[k["setup"]] * rate / q, [k["setup"], k["rate"]]))
        if p.finish_key:
            per_piece = max(values[k["finish_min"]], p.geometry.visible_area_m2 * values[k["finish_m2"]])
            lines.append(Line("finishing", p.part_id, None, p.name, n * per_piece, [k["finish_m2"], k["finish_min"]]))
        lines.append(Line("tooling", p.part_id, None, p.name, values[k["tooling"]] / q, [k["tooling"]]))
    for it in inputs.items:
        qty_val = values[it.qty_key] if it.qty_key else it.quantity
        unit_cost = values[it.cost_key] / 60 if it.unit == "min" else values[it.cost_key]
        keys = [it.cost_key] + ([it.qty_key] if it.qty_key else [])
        category = it.kind if it.kind in ("bought_in", "assembly", "packaging") else "bought_in"
        lines.append(Line(category, None, it.item_id, it.name, qty_val * unit_cost, keys))
    return lines


def total(lines: list[Line]) -> float:
    return sum(line.amount for line in lines)


def _ranges(inputs: CostInputs, quantity: float) -> tuple[list[Line], list[tuple[float, float]], tuple[float, float]]:
    """Midpoint lines plus root-sum-square (low, high) per line and for the total."""
    mids = inputs.mids()
    base_lines = evaluate(inputs, mids, quantity)
    base_total = total(base_lines)
    n = len(base_lines)
    lo_sq, hi_sq = [0.0] * n, [0.0] * n
    tot_lo_sq = tot_hi_sq = 0.0
    used = {k for line in base_lines for k in line.keys}
    for key in used:
        lo_v, hi_v = inputs.assumptions[key].widened(inputs.spread)
        for v in (lo_v, hi_v):
            lines = evaluate(inputs, {**mids, key: v}, quantity)
            for i, (b, ln) in enumerate(zip(base_lines, lines)):
                d = ln.amount - b.amount
                if d < 0:
                    lo_sq[i] += d * d
                else:
                    hi_sq[i] += d * d
            dt = total(lines) - base_total
            if dt < 0:
                tot_lo_sq += dt * dt
            else:
                tot_hi_sq += dt * dt
    per_line = [(max(b.amount - math.sqrt(lo), 0.0), b.amount + math.sqrt(hi)) for b, lo, hi in zip(base_lines, lo_sq, hi_sq)]
    total_range = (max(base_total - math.sqrt(tot_lo_sq), 0.0), base_total + math.sqrt(tot_hi_sq))
    return base_lines, per_line, total_range


def unit_cost_range(inputs: CostInputs, quantity: float) -> dict[str, float]:
    _, _, (low, high) = _ranges(inputs, quantity)
    mid = total(evaluate(inputs, inputs.mids(), quantity))
    worst_low = total(evaluate(inputs, inputs.lows(), quantity))
    worst_high = total(evaluate(inputs, inputs.highs(), quantity))
    return {"quantity": quantity, "low": round(low, 2), "mid": round(mid, 2), "high": round(high, 2),
            "worst_low": round(worst_low, 2), "worst_high": round(worst_high, 2)}


def part_unit_range(inputs: CostInputs, part_id: int, quantity_of_parts: float) -> dict[str, float] | None:
    """Cost of ONE piece of a part when `quantity_of_parts` pieces are ordered (for quote comparison)."""
    spec = next((p for p in inputs.parts if p.part_id == part_id), None)
    if spec is None:
        return None
    products = max(quantity_of_parts / max(spec.quantity, 1), 1.0)
    sub = CostInputs(assumptions=inputs.assumptions, parts=[spec], items=[], spread=inputs.spread)
    r = unit_cost_range(sub, products)
    return {k: (round(v / spec.quantity, 2) if k != "quantity" else quantity_of_parts) for k, v in r.items()}


def breakdown(inputs: CostInputs, quantity: float) -> list[dict[str, Any]]:
    """Each line at quantity Q with its midpoint and root-sum-square low/high."""
    base_lines, per_line, _ = _ranges(inputs, quantity)
    return [
        {"category": b.category, "part_id": b.part_id, "item_id": b.item_id, "label": b.label,
         "low": round(lo, 2), "mid": round(b.amount, 2), "high": round(hi, 2), "keys": b.keys}
        for b, (lo, hi) in zip(base_lines, per_line)
    ]


def sensitivity(inputs: CostInputs, quantity: float, step: float = 0.25, top: int | None = None) -> list[dict[str, Any]]:
    """Move each assumption ±step from its midpoint (others at midpoint); rank by unit-cost swing."""
    base_vals = inputs.mids()
    base = total(evaluate(inputs, base_vals, quantity))
    used = {k for line in evaluate(inputs, base_vals, quantity) for k in line.keys}
    results = []
    for key in sorted(used):
        a = inputs.assumptions[key]
        if a.mid == 0:
            continue
        up = total(evaluate(inputs, {**base_vals, key: a.mid * (1 + step)}, quantity))
        down = total(evaluate(inputs, {**base_vals, key: a.mid * (1 - step)}, quantity))
        swing = (up - down) / 2
        results.append({
            "key": key, "label": a.label, "group": a.group, "unit": a.unit,
            "value": round(a.mid, 4), "confidence": a.confidence, "verified": a.verified, "source": a.source,
            "cost_down": round(down, 2), "cost_up": round(up, 2), "swing": round(swing, 2),
            "swing_pct": round(swing / base * 100, 1) if base else 0.0,
        })
    results.sort(key=lambda r: -abs(r["swing"]))
    return results[:top] if top else results


def volume_table(inputs: CostInputs, quantities: list[float]) -> list[dict[str, float]]:
    return [unit_cost_range(inputs, q) for q in quantities]

