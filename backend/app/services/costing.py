"""Glue between projects (DB, CAD, rules) and the pure cost model."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from sqlalchemy.orm import Session

from app.cad import export, faro
from app.costing.data import CostData, load_cost_data
from app.costing.model import (
    CATEGORY_ORDER,
    Assumption,
    CostInputs,
    ItemSpec,
    PartGeometry,
    PartSpec,
    breakdown,
    part_quantities,
    part_unit_range,
    sensitivity,
    unit_cost_range,
    volume_table,
)
from app.models import CostItem, Part, Project
from app.rules.data import RuleSet, load_rules
from app.rules.match import match_finishes, match_material, match_process
from app.services.cad import current_parameters, latest_model
from app.services.recommendations import project_recommendations
from app.services.templates import load_template

TOP_SENSITIVITY = 5


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


@lru_cache(maxsize=16)
def _geometry_from_params(params_json: str) -> dict[str, Any]:
    params = json.loads(params_json)
    if not faro.validate(params).ok:
        return {}
    return export.part_info(faro.build(params))


def part_geometry(project: Project) -> tuple[dict[str, Any], str]:
    """Per-part volume/size from the latest CAD, else from an in-memory build of the current parameters."""
    latest = latest_model(project)
    if latest is not None:
        return latest.part_info, f"CAD v{latest.version}"
    if project.template == "faro":
        info = _geometry_from_params(json.dumps(current_parameters(project), sort_keys=True))
        if info:
            return info, "current CAD parameters (not yet generated)"
    return {}, "no CAD geometry"


# ---------------------------------------------------------------------------
# Default cost items
# ---------------------------------------------------------------------------


def default_items(project: Project, cost: CostData | None = None) -> list[CostItem]:
    """Template cost items for the project's current power type (undecided -> mains set)."""
    if not project.template:
        return []
    cost = cost or load_cost_data()
    tpl = load_template(project.template)
    power = (project.requirements or {}).get("power_type", "undecided")
    effective_power = "mains" if power == "undecided" else power
    params = current_parameters(project)
    items = []
    for i, spec in enumerate(tpl.get("cost_items", [])):
        if spec.get("power") and spec["power"] != effective_power:
            continue
        qty = float(params.get(spec["quantity_param"], 1)) if spec.get("quantity_param") else float(spec.get("quantity", 1))
        price = cost.bought_in.get(spec.get("price_key") or "")
        note = ""
        if spec.get("power") and power == "undecided":
            note = "Power type undecided: assumes mains."
        items.append(CostItem(
            project_id=project.id,
            kind=spec["kind"],
            name=spec.get("name") or (price.name if price else spec.get("price_key", "Item")),
            quantity=qty,
            unit=spec.get("unit", "pcs"),
            unit_cost_low=price.gbp.low if price else None,
            unit_cost_high=price.gbp.high if price else None,
            price_key=spec.get("price_key"),
            source=price.source if price else "model-generated",
            confidence=price.confidence if price else spec.get("confidence", "low"),
            verified=price.verified if price else False,
            notes=note,
            sort_order=i,
        ))
    return items


def reset_items(session: Session, project: Project) -> list[CostItem]:
    session.query(CostItem).filter(CostItem.project_id == project.id).delete()
    items = default_items(project)
    session.add_all(items)
    session.commit()
    return items


# ---------------------------------------------------------------------------
# Building model inputs
# ---------------------------------------------------------------------------


def _effective(part: Part, rec: dict[str, Any], rules: RuleSet) -> tuple[str | None, str | None, str]:
    r = rec.get("recommendation") or {}
    proc = match_process(rules, part.process) if part.process else None
    mat = match_material(rules, part.material) if part.material else None
    basis = "decided" if (proc or mat) else "recommended"
    return proc or r.get("process_key"), mat or r.get("material_key"), basis


def _add(assumptions: dict[str, Assumption], a: Assumption) -> None:
    assumptions.setdefault(a.key, a)


def build_inputs(session: Session, project: Project) -> tuple[CostInputs, dict[str, Any]]:
    """Model inputs for a project plus context (skipped parts, geometry source, part details)."""
    rules = load_rules()
    cost = load_cost_data()
    recs = {r["part_id"]: r for r in project_recommendations(project)}
    geometry, geometry_source = part_geometry(project)
    assumptions: dict[str, Assumption] = {}
    parts: list[PartSpec] = []
    skipped: list[dict[str, str]] = []
    details: dict[int, dict[str, Any]] = {}

    labour = cost.general["labour_gbp_per_hr"]
    _add(assumptions, Assumption("labour_rate", "Assembly labour rate", "£/hr", labour.value["low"], labour.value["high"],
                                 labour.confidence, labour.verified, labour.source, "Labour"))

    for part in project.parts:
        proc_key, mat_key, basis = _effective(part, recs.get(part.id, {}), rules)
        if proc_key == "bought_in" or part.material_category in ("electrical", "bought_in"):
            skipped.append({"name": part.name, "reason": "Bought-in: costed as a line item below, not from CAD."})
            continue
        geo = geometry.get(part.cad_key or "")
        if not geo:
            skipped.append({"name": part.name, "reason": "No CAD geometry for this part."})
            continue
        if proc_key not in cost.process_rates:
            skipped.append({"name": part.name, "reason": f"No cost rates for process '{part.process or proc_key}'."})
            continue
        if mat_key not in cost.material_prices or mat_key not in rules.materials:
            skipped.append({"name": part.name, "reason": f"No price for material '{part.material or mat_key}'."})
            continue

        proc_rule, mat_rule = rules.processes[proc_key], rules.materials[mat_key]
        rate, price = cost.process_rates[proc_key], cost.material_prices[mat_key]
        finishes = [f for f in match_finishes(rules, part.finish) if f in cost.finish_rates]
        finish_key = finishes[0] if finishes else None
        is_cnc = rate.min_per_cm3_removed is not None
        band = rules.tooling_cost[proc_rule.tooling_cost]

        spec = PartSpec(
            part_id=part.id, name=part.name, quantity=part.quantity, process_key=proc_key, process_name=proc_rule.name,
            material_key=mat_key, material_name=mat_rule.name, density_g_cm3=mat_rule.density_g_cm3 or 2.7,
            geometry=PartGeometry(geo["volume_mm3"], tuple(geo["size_mm"]), "axisymmetric" in (part.traits or [])),
            finish_key=finish_key, finish_name=cost_finish_name(rules, finish_key), basis=basis,
            cnc_allowance_mm=rate.stock_allowance_mm if is_cnc else None, tooling_band=proc_rule.tooling_cost,
        )
        parts.append(spec)
        details[part.id] = {"finishes_matched": finishes, "form": price.form}
        k = CostInputs(assumptions={}).keys_for_part(spec)
        prov = dict(confidence=rate.confidence, verified=rate.verified, source=rate.source)
        _add(assumptions, Assumption(k["price"], f"{mat_rule.name} price", "£/kg", price.gbp_per_kg.low,
                                     price.gbp_per_kg.high, price.confidence, price.verified, price.source, "Material prices"))
        _add(assumptions, Assumption(k["rate"], f"{proc_rule.name} machine rate", "£/hr", rate.machine_gbp_per_hr.low,
                                     rate.machine_gbp_per_hr.high, group="Machine rates", **prov))
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
            _add(assumptions, Assumption(k["finish_m2"], f"{fname} cost per m²", "£/m²", fr.gbp_per_m2.low, fr.gbp_per_m2.high,
                                         group="Finishing", **fprov))
            _add(assumptions, Assumption(k["finish_min"], f"{fname} minimum charge per part", "£", fr.min_per_part.low,
                                         fr.min_per_part.high, group="Finishing", **fprov))
        _add(assumptions, Assumption(k["tooling"], f"Tooling for {part.name.lower()} ({proc_rule.name.lower()})", "£",
                                     band.gbp_min, band.gbp_max, band.confidence, band.verified, band.source, "Tooling"))

    items: list[ItemSpec] = []
    db_items = session.query(CostItem).filter(CostItem.project_id == project.id).order_by(CostItem.sort_order, CostItem.id).all()
    for it in db_items:
        prov = dict(confidence=it.confidence, verified=it.verified, source=it.source)
        if it.unit == "min" and it.unit_cost_low is None:
            cost_key = "labour_rate"
            qty_key = f"item_qty:{it.id}"
            _add(assumptions, Assumption(qty_key, f"{it.name} time", "min", it.quantity, it.quantity, group="Labour", **prov))
        else:
            cost_key = f"item:{it.id}"
            qty_key = None
            low = it.unit_cost_low if it.unit_cost_low is not None else it.unit_cost_high or 0.0
            high = it.unit_cost_high if it.unit_cost_high is not None else low
            group = {"packaging": "Packaging", "assembly": "Labour"}.get(it.kind, "Bought-in components")
            _add(assumptions, Assumption(cost_key, f"{it.name} price" if it.unit == "pcs" else f"{it.name} rate",
                                         "£" if it.unit == "pcs" else "£/min", min(low, high), max(low, high), group=group, **prov))
        items.append(ItemSpec(it.id, it.kind, it.name, it.quantity, it.unit, cost_key, qty_key))

    spread = cost.value("confidence_spread")
    inputs = CostInputs(assumptions=assumptions, parts=parts, items=items, spread=spread)
    return inputs, {"skipped": skipped, "geometry_source": geometry_source, "details": details, "db_items": db_items}


def cost_finish_name(rules: RuleSet, key: str | None) -> str | None:
    return rules.finishes[key].name if key else None


# ---------------------------------------------------------------------------
# Plain-English explanations
# ---------------------------------------------------------------------------


def _money(a: Assumption) -> str:
    return f"£{a.low:,.2f}–£{a.high:,.2f}" if a.low != a.high else f"£{a.low:,.2f}"


def explain_line(line: dict[str, Any], inputs: CostInputs, ctx: dict[str, Any], quantity: float) -> str:
    A = inputs.assumptions
    mids = inputs.mids()
    if line["part_id"] is not None:
        p = next(s for s in inputs.parts if s.part_id == line["part_id"])
        k = inputs.keys_for_part(p)
        q = part_quantities(p, k, mids)
        each = f"{p.quantity} × " if p.quantity > 1 else ""
        form = ctx["details"].get(p.part_id, {}).get("form", "stock")
        if line["category"] == "material":
            if p.cnc_allowance_mm is not None:
                return (f"{each}{q['bought_kg']:.2f} kg of {p.material_name} {form}, machined down to a "
                        f"{q['finished_kg']:.2f} kg part ({q['removed_cm3']:.0f} cm³ cut away), at {_money(A[k['price']])}/kg.")
            return (f"{each}{q['bought_kg']:.2f} kg of {p.material_name} {form} for a {q['finished_kg']:.2f} kg part "
                    f"(the extra is trim and scrap), at {_money(A[k['price']])}/kg.")
        if line["category"] == "process":
            how = (f"{q['removed_cm3']:.0f} cm³ of cutting plus handling" if p.cnc_allowance_mm is not None
                   else "forming / cutting and handling")
            return (f"{each}about {q['minutes']:.0f} min per part ({how}) on {p.process_name.lower()} at "
                    f"{_money(A[k['rate']])}/hr.")
        if line["category"] == "setup":
            return (f"About {A[k['setup']].mid:.1f} h setting up the {p.process_name.lower()} job, shared across "
                    f"{quantity:,.0f} units.")
        if line["category"] == "finishing":
            return (f"{each}{p.finish_name} on about {p.geometry.visible_area_m2:.3f} m² of visible surface at "
                    f"{_money(A[k['finish_m2']])}/m², or the minimum charge of {_money(A[k['finish_min']])} if higher.")
        if line["category"] == "tooling":
            band = A[k["tooling"]]
            if band.high == 0:
                return f"No dedicated tooling needed for {p.process_name.lower()}."
            return (f"One-off {p.process_name.lower()} tooling ({_money(band)}) spread across {quantity:,.0f} units. "
                    "Falls quickly as volume grows.")
    it = next(i for i in inputs.items if i.item_id == line["item_id"])
    if it.unit == "min":
        minutes = A[it.qty_key].mid if it.qty_key else it.quantity
        return f"{minutes:.0f} min of {it.name.lower()} at {_money(A[it.cost_key])}/hr."
    qty = f"{it.quantity:g} × " if it.quantity != 1 else ""
    return f"{qty}{it.name} at {_money(A[it.cost_key])} each (bought in)."


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def reference_quantity(project: Project) -> tuple[int, str]:
    vol = (project.requirements or {}).get("production_volume")
    if vol:
        return int(vol), "project production volume"
    return int(load_rules().plan("assumed_volume_when_unknown")), "assumed volume (placeholder; production volume not set)"


def cost_report(session: Session, project: Project) -> dict[str, Any]:
    cost = load_cost_data()
    inputs, ctx = build_inputs(session, project)
    ref_q, ref_basis = reference_quantity(project)
    quantities = list(cost.value("volume_table"))
    project_vol = (project.requirements or {}).get("production_volume")
    if project_vol and project_vol not in quantities:
        quantities.append(int(project_vol))
    quantities.sort()

    lines = breakdown(inputs, ref_q)
    A = inputs.assumptions
    for line in lines:
        line["explanation"] = explain_line(line, inputs, ctx, ref_q)
        used = [A[k] for k in line["keys"]]
        line["unverified"] = any(not a.verified for a in used)
        line["confidence"] = min((a.confidence for a in used), key=["low", "medium", "high"].index, default="high")

    parts_out = []
    for p in inputs.parts:
        plines = [ln for ln in lines if ln["part_id"] == p.part_id]
        sub = unit_cost_range(CostInputs(assumptions=A, parts=[p], items=[], spread=inputs.spread), ref_q)
        parts_out.append({
            "part_id": p.part_id, "name": p.name, "quantity": p.quantity, "process": p.process_name,
            "material": p.material_name, "finish": p.finish_name, "basis": p.basis, "lines": plines,
            "low": sub["low"], "mid": sub["mid"], "high": sub["high"],
        })
    product_lines = [ln for ln in lines if ln["part_id"] is None]

    by_cat = {}
    for cat in CATEGORY_ORDER:
        cl = [ln for ln in lines if ln["category"] == cat]
        if cl:
            by_cat[cat] = {"low": round(sum(x["low"] for x in cl), 2), "high": round(sum(x["high"] for x in cl), 2),
                           "mid": round(sum(x["mid"] for x in cl), 2)}

    step = float(cost.value("sensitivity_step"))
    sens = sensitivity(inputs, ref_q, step)
    vt = volume_table(inputs, quantities)
    for row in vt:
        row["is_project_volume"] = bool(project_vol) and row["quantity"] == project_vol

    used_keys = {k for ln in lines for k in ln["keys"]}
    assumptions = [
        {"key": a.key, "label": a.label, "group": a.group, "unit": a.unit, "low": a.low, "high": a.high,
         "widened": [round(x, 4) for x in a.widened(inputs.spread)], "confidence": a.confidence,
         "verified": a.verified, "source": a.source}
        for a in sorted((A[k] for k in used_keys), key=lambda a: (a.group, a.label))
    ]
    notes = [
        "Process and material come from your decision on each part, or the rules engine's recommendation where none is set.",
        f"Geometry from {ctx['geometry_source']}.",
        "Each range is the cheapest and dearest end of every input, widened for low-confidence inputs.",
        "Setup and tooling are one-off costs spread over the quantity, so unit cost falls with volume.",
    ]
    return {
        "currency": "GBP",
        "reference_quantity": ref_q,
        "reference_basis": ref_basis,
        "unit_cost": unit_cost_range(inputs, ref_q),
        "volumes": vt,
        "parts": parts_out,
        "product_lines": product_lines,
        "categories": by_cat,
        "sensitivity": {"step": step, "top": sens[:TOP_SENSITIVITY], "count": len(sens)},
        "skipped": ctx["skipped"],
        "assumptions": assumptions,
        "spread": inputs.spread,
        "uses_unverified_data": any(not a["verified"] for a in assumptions),
        "has_items": bool(ctx["db_items"]),
        "can_load_defaults": bool(project.template),
        "notes": notes,
    }


def model_part_estimate(inputs: CostInputs, part: Part, quantity_of_parts: float) -> dict[str, Any] | None:
    """Model unit-price range for one piece of `part` when ordering `quantity_of_parts` pieces."""
    r = part_unit_range(inputs, part.id, quantity_of_parts)
    if r is None:
        return None
    return {"low": r["low"], "high": r["high"], "currency": "GBP",
            "basis": f"Cost model at {quantity_of_parts:,.0f} pcs (unverified rates)", "source": "model"}
