"""Cost-rate seed data (backend/seed/cost/*.yaml).

Same provenance contract as the rules data: every entry needs `source` and
`confidence`; `verified` defaults to False. Loading fails loudly otherwise.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, model_validator

from app.config import SEED_DIR
from app.rules.data import Provenance, RuleSet, RulesDataError, load_rules


class Span(BaseModel):
    low: float
    high: float

    @model_validator(mode="after")
    def _ordered(self) -> "Span":
        if self.low < 0 or self.high < self.low:
            raise ValueError(f"invalid range {self.low}–{self.high} (need 0 <= low <= high)")
        return self


class MaterialPrice(Provenance):
    material: str
    form: str
    gbp_per_kg: Span
    # Cost-only materials (e.g. brass for a premium edition) are not in the rules data
    # and must give their own density.
    cost_only: bool = False
    density_g_cm3: float | None = None


class ProcessRate(Provenance):
    process: str
    machine_gbp_per_hr: Span
    setup_hours: Span
    cycle_min: Span
    cycle_min_per_kg: Span
    material_utilisation: Span
    min_per_cm3_removed: Span | None = None
    stock_allowance_mm: float | None = None
    lead_time_weeks: Span | None = None


class FinishRate(Provenance):
    finish: str
    gbp_per_m2: Span
    min_per_part: Span


class GeneralValue(Provenance):
    key: str
    value: Any
    plain_language: str


class BoughtInPrice(Provenance):
    key: str
    name: str
    gbp: Span


class Region(Provenance):
    key: str
    name: str
    machine: Span
    labour: Span
    tooling: Span
    finishing: Span
    freight_duty_pct: Span
    lead_time_note: str = ""


class RouteItem(BaseModel):
    price_key: str
    quantity: float | None = None
    quantity_param: str | None = None


class RouteChange(Provenance):
    key: str
    processes: list[str]
    traits_any: list[str] = []
    design_change: str
    items: list[RouteItem] = []
    safety: str = ""


class PricingValue(Provenance):
    key: str
    value: float
    plain_language: str


class CostData(BaseModel):
    material_prices: dict[str, MaterialPrice]
    process_rates: dict[str, ProcessRate]
    finish_rates: dict[str, FinishRate]
    general: dict[str, GeneralValue]
    bought_in: dict[str, BoughtInPrice]
    regions: dict[str, Region]
    route_changes: dict[str, RouteChange]
    pricing: dict[str, PricingValue]

    def value(self, key: str) -> Any:
        return self.general[key].value


_FILES: dict[str, tuple[str, type[Provenance], str]] = {
    "material_prices.yaml": ("material_prices", MaterialPrice, "material"),
    "process_rates.yaml": ("process_rates", ProcessRate, "process"),
    "finish_rates.yaml": ("finish_rates", FinishRate, "finish"),
    "general.yaml": ("general", GeneralValue, "key"),
    "bought_in.yaml": ("bought_in", BoughtInPrice, "key"),
    "regions.yaml": ("regions", Region, "key"),
    "route_changes.yaml": ("route_changes", RouteChange, "key"),
    "pricing.yaml": ("pricing", PricingValue, "key"),
}
REQUIRED_PRICING = {"vat_rate", "dtc_factory_share", "retailer_margin", "wholesale_factory_share", "close_band"}
REQUIRED_GENERAL = {"labour_gbp_per_hr", "confidence_spread", "volume_table", "sensitivity_step"}


def load_cost_data_from(directory: Path, rules: RuleSet | None = None) -> CostData:
    rules = rules or load_rules()
    data: dict[str, Any] = {}
    for filename, (top, model, index) in _FILES.items():
        with (directory / filename).open() as f:
            raw = yaml.safe_load(f) or {}
        entries = raw.get(top)
        if not isinstance(entries, list):
            raise RulesDataError(f"{filename}: expected a list under '{top}'")
        parsed = []
        for i, entry in enumerate(entries):
            try:
                parsed.append(model.model_validate(entry))
            except Exception as e:
                raise RulesDataError(f"{filename} entry {i}: {e}") from e
        keyed = {getattr(e, index): e for e in parsed}
        if len(keyed) != len(parsed):
            raise RulesDataError(f"{filename}: duplicate '{index}' values")
        data[top] = keyed
    cost = CostData(**data)

    # Cross-checks against the rules data.
    for k, m in cost.material_prices.items():
        if m.cost_only:
            if not m.density_g_cm3:
                raise RulesDataError(f"material_prices: cost-only material {k} needs density_g_cm3")
        elif k not in rules.materials:
            raise RulesDataError(f"material_prices: unknown material {k}")
    for k in cost.process_rates:
        if k not in rules.processes:
            raise RulesDataError(f"process_rates: unknown process {k}")
    for k in cost.finish_rates:
        if k not in rules.finishes:
            raise RulesDataError(f"finish_rates: unknown finish {k}")
    missing = REQUIRED_GENERAL - set(cost.general)
    if missing:
        raise RulesDataError(f"general.yaml: missing {sorted(missing)}")
    spread = cost.value("confidence_spread")
    if set(spread) != {"low", "medium", "high"}:
        raise RulesDataError("general.yaml: confidence_spread needs low, medium and high")
    if "uk" not in cost.regions:
        raise RulesDataError("regions.yaml: needs a 'uk' baseline region")
    for rc in cost.route_changes.values():
        for pk in rc.processes:
            if pk not in rules.processes:
                raise RulesDataError(f"route_changes {rc.key}: unknown process {pk}")
        for it in rc.items:
            if it.price_key not in cost.bought_in:
                raise RulesDataError(f"route_changes {rc.key}: unknown price_key {it.price_key}")
    missing_p = REQUIRED_PRICING - set(cost.pricing)
    if missing_p:
        raise RulesDataError(f"pricing.yaml: missing {sorted(missing_p)}")
    cnc = cost.process_rates.get("cnc_machining")
    if cnc and (cnc.min_per_cm3_removed is None or cnc.stock_allowance_mm is None):
        raise RulesDataError("process_rates: cnc_machining needs min_per_cm3_removed and stock_allowance_mm")
    return cost


@lru_cache
def load_cost_data() -> CostData:
    return load_cost_data_from(SEED_DIR / "cost")
