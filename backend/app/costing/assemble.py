"""Assemble cost-model inputs from a project snapshot and a configuration.

Pure: no database access. The service layer takes a `Snapshot` of the project
once (parts, routes, geometry, cost items); `assemble()` then turns it into
`CostInputs` for any `CostConfig` (process route overrides, scenarios, region,
premium edition), so route comparison and scenario search are cheap.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable

from app.costing.data import CostData
from app.costing.model import Assumption, CostInputs, ItemSpec, PartGeometry, PartSpec
from app.rules.data import RuleSet
from app.rules.match import match_finishes

# Processes that make parts from sheet: the part is a shell of roughly the sheet thickness.
SHEET_FORMED = {"metal_spinning", "deep_drawing", "sheet_forming"}


@dataclass(frozen=True)
class RouteChoice:
    process_key: str
    material_key: str
    tooling: str | None = None  # override tooling band (e.g. "none" for stock tube)
    label: str = ""


@dataclass
class SnapPart:
    part_id: int
    cad_key: str | None
    name: str
    quantity: int
    material_category: str
    traits: list[str]
    derived_traits: list[str]
    finish_text: str
    process_key: str | None  # effective (decided, else recommended)
    material_key: str | None
    basis: str  # decided | recommended
    viable: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SnapItem:
    item_id: int
    kind: str
    name: str
    quantity: float
    unit: str
    unit_cost_low: float | None
    unit_cost_high: float | None
    price_key: str | None
    source: str
    confidence: str
    verified: bool


@dataclass
class Snapshot:
    parts: list[SnapPart]
    items: list[SnapItem]
    params: dict[str, Any]
    geometry: dict[str, Any]
    geometry_source: str
    # Geometry for a different overall height (scaled parameters); None if not available.
    geometry_for_height: Callable[[float], dict[str, Any]] | None = None


@dataclass
class ExtraItem:
    price_key: str
    quantity: float
    kind: str = "bought_in"
    part_id: int | None = None
    origin: str = ""  # human-readable reason, e.g. "Base: spun route"


@dataclass
class CostConfig:
    routes: dict[str, RouteChoice] = field(default_factory=dict)  # by cad_key
    removed_parts: set[str] = field(default_factory=set)
    add_items: list[ExtraItem] = field(default_factory=list)
    remove_price_keys: set[str] = field(default_factory=set)
    assembly_delta_min: tuple[float, float] = (0.0, 0.0)
    height_mm: float | None = None
    region: str = "uk"
    material_overrides: dict[str, str] = field(default_factory=dict)  # by cad_key
    finish_overrides: dict[str, str] = field(default_factory=dict)  # by cad_key, finish key

    def merged(self, other: "CostConfig") -> "CostConfig":
        lo1, hi1 = self.assembly_delta_min
        lo2, hi2 = other.assembly_delta_min
        return CostConfig(
            routes={**self.routes, **other.routes},
            removed_parts=self.removed_parts | other.removed_parts,
            add_items=self.add_items + other.add_items,
            remove_price_keys=self.remove_price_keys | other.remove_price_keys,
            assembly_delta_min=(lo1 + lo2, hi1 + hi2),
            height_mm=other.height_mm or self.height_mm,
            region=other.region if other.region != "uk" else self.region,
            material_overrides={**self.material_overrides, **other.material_overrides},
            finish_overrides={**self.finish_overrides, **other.finish_overrides},
        )


def _add(assumptions: dict[str, Assumption], a: Assumption) -> None:
    assumptions.setdefault(a.key, a)


def _scaled(a: Assumption, low_mult: float, high_mult: float) -> Assumption:
    return replace(a, low=a.low * low_mult, high=a.high * high_mult)


def route_changes_for(cost: CostData, process_key: str, traits: set[str]) -> list[Any]:
    return [
        rc for rc in cost.route_changes.values()
        if process_key in rc.processes and (not rc.traits_any or traits & set(rc.traits_any))
    ]


def assemble(snapshot: Snapshot, config: CostConfig, rules: RuleSet, cost: CostData) -> tuple[CostInputs, dict[str, Any]]:
    """CostInputs for one configuration, plus context for explanations and reporting."""
    assumptions: dict[str, Assumption] = {}
    parts: list[PartSpec] = []
    skipped: list[dict[str, str]] = []
    details: dict[int, dict[str, Any]] = {}
    design_changes: list[dict[str, Any]] = []
    flags: list[dict[str, str]] = []
    extra: list[ExtraItem] = list(config.add_items)

    region = cost.regions[config.region]
    geometry = snapshot.geometry
    if config.height_mm and snapshot.geometry_for_height is not None:
        geometry = snapshot.geometry_for_height(config.height_mm) or geometry

    labour = cost.general["labour_gbp_per_hr"]
    _add(assumptions, _scaled(
        Assumption("labour_rate", "Assembly labour rate", "£/hr", labour.value["low"], labour.value["high"],
                   labour.confidence, labour.verified, labour.source, "Labour"),
        region.labour.low, region.labour.high))

    for sp in snapshot.parts:
        if sp.cad_key and sp.cad_key in config.removed_parts:
            skipped.append({"name": sp.name, "reason": "Removed by a design-change scenario."})
            continue
        choice = config.routes.get(sp.cad_key or "")
        proc_key = choice.process_key if choice else sp.process_key
        mat_key = choice.material_key if choice else sp.material_key
        basis = "scenario" if choice else sp.basis
        if sp.cad_key in config.material_overrides:
            mat_key = config.material_overrides[sp.cad_key]
        if proc_key == "bought_in" or sp.material_category in ("electrical", "bought_in"):
            skipped.append({"name": sp.name, "reason": "Bought-in: costed as a line item below, not from CAD."})
            continue
        geo = geometry.get(sp.cad_key or "")
        if not geo:
            skipped.append({"name": sp.name, "reason": "No CAD geometry for this part."})
            continue
        if proc_key not in cost.process_rates:
            skipped.append({"name": sp.name, "reason": f"No cost rates for process '{proc_key}'."})
            continue
        price = cost.material_prices.get(mat_key or "")
        mat_rule = rules.materials.get(mat_key or "")
        if price is None or (mat_rule is None and not price.cost_only):
            skipped.append({"name": sp.name, "reason": f"No price for material '{mat_key}'."})
            continue

        proc_rule = rules.processes[proc_key]
        rate = cost.process_rates[proc_key]
        if sp.cad_key in config.finish_overrides:
            finish_key = config.finish_overrides[sp.cad_key]
        else:
            finishes = [f for f in match_finishes(rules, sp.finish_text) if f in cost.finish_rates]
            finish_key = finishes[0] if finishes else None
        is_cnc = rate.min_per_cm3_removed is not None
        band_key = (choice.tooling if choice and choice.tooling else proc_rule.tooling_cost)
        band = rules.tooling_cost[band_key]
        mat_name = mat_rule.name if mat_rule else f"{mat_key.capitalize()} ({price.form})"
        density = (mat_rule.density_g_cm3 if mat_rule else None) or price.density_g_cm3 or 2.7

        spec = PartSpec(
            part_id=sp.part_id, name=sp.name, quantity=sp.quantity, process_key=proc_key, process_name=proc_rule.name,
            material_key=mat_key, material_name=mat_name, density_g_cm3=density,
            geometry=PartGeometry(geo["volume_mm3"], tuple(geo["size_mm"]), "axisymmetric" in sp.traits),
            finish_key=finish_key, finish_name=rules.finishes[finish_key].name if finish_key else None, basis=basis,
            cnc_allowance_mm=rate.stock_allowance_mm if is_cnc else None, tooling_band=band_key,
            formed_shell_mm=(float(snapshot.params.get("wall_thickness") or 0) or None) if proc_key in SHEET_FORMED else None,
        )
        parts.append(spec)
        details[sp.part_id] = {"form": price.form, "route_label": choice.label if choice else ""}

        # Design changes this route needs, and the parts they add.
        traits = set(sp.traits) | set(sp.derived_traits)
        for rc in route_changes_for(cost, proc_key, traits):
            design_changes.append({"part": sp.name, "part_id": sp.part_id, "key": rc.key, "text": " ".join(rc.design_change.split()),
                                   "verified": rc.verified})
            if rc.safety:
                flags.append({"kind": "safety", "part": sp.name, "message": rc.safety})
            for it in rc.items:
                qty = float(snapshot.params.get(it.quantity_param, 1)) if it.quantity_param else float(it.quantity or 1)
                extra.append(ExtraItem(it.price_key, qty, part_id=sp.part_id, origin=f"{sp.name}: {proc_rule.name.lower()} route"))

        k = CostInputs(assumptions={}).keys_for_part(spec)
        prov = dict(confidence=rate.confidence, verified=rate.verified, source=rate.source)
        _add(assumptions, Assumption(k["price"], f"{mat_name} price", "£/kg", price.gbp_per_kg.low,
                                     price.gbp_per_kg.high, price.confidence, price.verified, price.source, "Material prices"))
        _add(assumptions, _scaled(Assumption(k["rate"], f"{proc_rule.name} machine rate", "£/hr", rate.machine_gbp_per_hr.low,
                                             rate.machine_gbp_per_hr.high, group="Machine rates", **prov),
                                  region.machine.low, region.machine.high))
        _add(assumptions, Assumption(k["setup"], f"{proc_rule.name} setup time per batch", "hours", rate.setup_hours.low,
                                     rate.setup_hours.high, group="Setup", **prov))
        _add(assumptions, Assumption(k["cycle"], f"{proc_rule.name} handling time per part", "min", rate.cycle_min.low,
                                     rate.cycle_min.high, group="Cycle times", **prov))
        _add(assumptions, Assumption(k["cycle_kg"], f"{proc_rule.name} extra time per kg", "min/kg",
                                     rate.cycle_min_per_kg.low, rate.cycle_min_per_kg.high, group="Cycle times", **prov))
        _add(assumptions, Assumption(k["util"], f"{proc_rule.name} material bought per kg of part", "×",
                                     rate.material_utilisation.low, rate.material_utilisation.high, group="Scrap / yield", **prov))
        if is_cnc:
            _add(assumptions, Assumption(k["removal"], f"{proc_rule.name} time per cm³ cut away", "min/cm³",
                                         rate.min_per_cm3_removed.low, rate.min_per_cm3_removed.high, group="Cycle times", **prov))
        if finish_key:
            fr = cost.finish_rates[finish_key]
            fprov = dict(confidence=fr.confidence, verified=fr.verified, source=fr.source)
            fname = rules.finishes[finish_key].name
            fl, fh = region.finishing.low, region.finishing.high
            _add(assumptions, _scaled(Assumption(k["finish_m2"], f"{fname} cost per m²", "£/m²", fr.gbp_per_m2.low,
                                                 fr.gbp_per_m2.high, group="Finishing", **fprov), fl, fh))
            _add(assumptions, _scaled(Assumption(k["finish_min"], f"{fname} minimum charge per part", "£", fr.min_per_part.low,
                                                 fr.min_per_part.high, group="Finishing", **fprov), fl, fh))
        tool_label = "stock material, no tooling" if band.gbp_max == 0 else proc_rule.name.lower()
        _add(assumptions, _scaled(Assumption(k["tooling"], f"Tooling for {sp.name.lower()} ({tool_label})", "£",
                                             band.gbp_min, band.gbp_max, band.confidence, band.verified, band.source, "Tooling"),
                                  region.tooling.low, region.tooling.high))

    # Product-level items: project items minus removals, plus scenario / route extras.
    items: list[ItemSpec] = []
    minute_items_adjusted = False
    for it in snapshot.items:
        if it.price_key and it.price_key in config.remove_price_keys:
            continue
        prov = dict(confidence=it.confidence, verified=it.verified, source=it.source)
        if it.unit == "min" and it.unit_cost_low is None:
            cost_key, qty_key = "labour_rate", f"item_qty:{it.item_id}"
            lo, hi = it.quantity, it.quantity
            if not minute_items_adjusted and config.assembly_delta_min != (0.0, 0.0):
                # Scenarios that simplify assembly shorten the first minute-based item.
                d_lo, d_hi = config.assembly_delta_min
                lo, hi = sorted((max(it.quantity + d_lo, 1.0), max(it.quantity + d_hi, 1.0)))
                minute_items_adjusted = True
            _add(assumptions, Assumption(qty_key, f"{it.name} time", "min", lo, hi, group="Labour", **prov))
        else:
            cost_key, qty_key = f"item:{it.item_id}", None
            low = it.unit_cost_low if it.unit_cost_low is not None else it.unit_cost_high or 0.0
            high = it.unit_cost_high if it.unit_cost_high is not None else low
            group = {"packaging": "Packaging", "assembly": "Labour"}.get(it.kind, "Bought-in components")
            _add(assumptions, Assumption(cost_key, f"{it.name} price" if it.unit == "pcs" else f"{it.name} rate",
                                         "£" if it.unit == "pcs" else "£/min", min(low, high), max(low, high), group=group, **prov))
        items.append(ItemSpec(it.item_id, it.kind, it.name, it.quantity, it.unit, cost_key, qty_key))

    extras_ctx: dict[int, ExtraItem] = {}
    for n, ex in enumerate(extra, start=1):
        if ex.price_key in config.remove_price_keys:
            continue
        price = cost.bought_in[ex.price_key]
        item_id = -n
        key = f"extra:{ex.price_key}"
        group = "Finishing" if ex.kind == "finishing" else "Bought-in components"
        _add(assumptions, Assumption(key, f"{price.name} price", "£", price.gbp.low, price.gbp.high,
                                     price.confidence, price.verified, price.source, group))
        items.append(ItemSpec(item_id, ex.kind, price.name, ex.quantity, "pcs", key, None, ex.part_id))
        extras_ctx[item_id] = ex

    overhead_key = None
    if region.freight_duty_pct.high > 0:
        overhead_key = "region_freight_duty"
        _add(assumptions, Assumption(overhead_key, f"Freight and duty to the UK from {region.name}", "%",
                                     region.freight_duty_pct.low, region.freight_duty_pct.high,
                                     region.confidence, region.verified, region.source, "Region"))

    inputs = CostInputs(assumptions=assumptions, parts=parts, items=items, spread=cost.value("confidence_spread"),
                        overhead_key=overhead_key)
    ctx = {
        "skipped": skipped, "details": details, "geometry_source": snapshot.geometry_source,
        "design_changes": design_changes, "flags": flags, "extras": extras_ctx, "region": region,
    }
    return inputs, ctx
