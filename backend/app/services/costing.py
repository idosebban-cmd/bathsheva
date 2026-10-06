"""Glue between projects (DB, CAD, rules) and the pure cost model."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from sqlalchemy.orm import Session

from app.cad import export, faro
from app.costing.assemble import CostConfig, SnapItem, SnapPart, Snapshot, assemble
from app.costing.data import CostData, load_cost_data
from app.costing.model import (
    CATEGORY_ORDER,
    Assumption,
    CostInputs,
    breakdown,
    effective_volume_cm3,
    part_quantities,
    part_unit_range,
    sensitivity,
    unit_cost_range,
    volume_table,
)
from app.models import CostItem, Part, Project
from app.rules.data import RuleSet, load_rules
from app.rules.match import match_material, match_process
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
            price_basis=price.price_basis if price else "model_estimate",
            basis_quantity=price.basis_quantity if price else None,
            discount_class=price.discount_class if price else None,
            notes=note or (" ".join(price.notes.split()) if price else ""),
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

# Parameters that stay fixed when the lamp is scaled to a new height.
UNSCALED_PARAMS = {"wall_thickness", "lantern_wall_thickness", "cable_hole_diameter", "mounting_hole_diameter",
                   "mounting_hole_count", "band_position"}


def scaled_parameters(params: dict[str, Any], height_mm: float) -> dict[str, Any]:
    """Scale every linear dimension with overall height; wall thicknesses and hole sizes stay put."""
    f = height_mm / float(params["overall_height"])
    out = {}
    for k, v in params.items():
        if k in UNSCALED_PARAMS:
            out[k] = v
        else:
            out[k] = round(float(v) * f, 2)
    out["overall_height"] = height_mm
    return out


def _effective(part: Part, rec: dict[str, Any], rules: RuleSet) -> tuple[str | None, str | None, str]:
    r = rec.get("recommendation") or {}
    proc = match_process(rules, part.process) if part.process else None
    mat = match_material(rules, part.material) if part.material else None
    if part.material and not mat and part.material.strip().lower() in load_cost_data().material_prices:
        mat = part.material.strip().lower()  # cost-only material such as brass
    basis = "decided" if (proc or mat) else "recommended"
    return proc or r.get("process_key"), mat or r.get("material_key"), basis


def snapshot(session: Session, project: Project) -> Snapshot:
    """Everything the cost model needs from the database, read once."""
    rules = load_rules()
    recs = {r["part_id"]: r for r in project_recommendations(project)}
    geometry, geometry_source = part_geometry(project)
    params = current_parameters(project) if project.template else {}
    parts = []
    for part in project.parts:
        rec = recs.get(part.id, {})
        proc, mat, basis = _effective(part, rec, rules)
        derived = faro.derived_traits(part.cad_key, params) if project.template == "faro" and part.cad_key else []
        parts.append(SnapPart(
            part_id=part.id, cad_key=part.cad_key, name=part.name, quantity=part.quantity,
            material_category=part.material_category, traits=list(part.traits or []), derived_traits=derived,
            finish_text=part.finish, process_key=proc, material_key=mat, basis=basis, viable=rec.get("viable", []),
        ))
    db_items = session.query(CostItem).filter(CostItem.project_id == project.id).order_by(CostItem.sort_order, CostItem.id).all()
    items = [SnapItem(it.id, it.kind, it.name, it.quantity, it.unit, it.unit_cost_low, it.unit_cost_high, it.price_key,
                      it.source, it.confidence, it.verified, it.price_basis or "model_estimate", it.basis_quantity,
                      it.discount_class) for it in db_items]

    def for_height(h: float) -> dict[str, Any]:
        if project.template != "faro" or not params:
            return {}
        return _geometry_from_params(json.dumps(scaled_parameters(params, h), sort_keys=True))

    return Snapshot(parts=parts, items=items, params=params, geometry=geometry, geometry_source=geometry_source,
                    geometry_for_height=for_height,
                    volume_discounts=dict((project.cost_settings or {}).get("volume_discounts") or {}))


# ---------------------------------------------------------------------------
# Cost settings (volume discounts)
# ---------------------------------------------------------------------------


def cost_settings(project: Project) -> dict[str, Any]:
    """Volume-discount assumptions: seed defaults overlaid with the project's edits."""
    cost = load_cost_data()
    user = (project.cost_settings or {}).get("volume_discounts") or {}
    out = {}
    for cls, g in cost.discount_classes().items():
        edited = cls in user
        v = user.get(cls, g.value)
        out[cls] = {
            "low": float(v["low"]), "high": float(v["high"]), "from_quantity": g.value.get("from_quantity", 0),
            "default": {"low": g.value["low"], "high": g.value["high"]}, "edited": edited,
            "source": "user (project setting)" if edited else g.source,
            "confidence": g.confidence, "verified": False, "plain_language": " ".join(g.plain_language.split()),
        }
    return {"volume_discounts": out}


def update_cost_settings(session: Session, project: Project, discounts: dict[str, dict[str, float] | None]) -> dict[str, Any]:
    from fastapi import HTTPException

    classes = load_cost_data().discount_classes()
    current = dict((project.cost_settings or {}).get("volume_discounts") or {})
    for cls, v in discounts.items():
        if cls not in classes:
            raise HTTPException(422, f"Unknown volume discount class {cls!r}")
        if v is None:  # back to the default
            current.pop(cls, None)
            continue
        lo, hi = float(v.get("low", -1)), float(v.get("high", -1))
        if not 0 < lo <= hi <= 1:
            raise HTTPException(422, "Volume discount must be a share of the small-quantity price: 0 < low ≤ high ≤ 1")
        current[cls] = {"low": lo, "high": hi}
    project.cost_settings = {**(project.cost_settings or {}), "volume_discounts": current}
    session.commit()
    return cost_settings(project)


def build_inputs(session: Session, project: Project, config: CostConfig | None = None,
                 snap: Snapshot | None = None) -> tuple[CostInputs, dict[str, Any]]:
    """Model inputs for a project (optionally under a configuration) plus context."""
    snap = snap or snapshot(session, project)
    inputs, ctx = assemble(snap, config or CostConfig(), load_rules(), load_cost_data())
    ctx["db_items"] = snap.items
    return inputs, ctx


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
            shell = ""
            if p.formed_shell_mm and effective_volume_cm3(p) < p.geometry.volume_cm3 - 1e-6:
                shell = f" (costed as a {p.formed_shell_mm:g} mm formed shell; the CAD body is solid)"
            return (f"{each}{q['bought_kg']:.2f} kg of {p.material_name} {form} for a {q['finished_kg']:.2f} kg part{shell} "
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
    if line["category"] == "freight_duty":
        a = A[inputs.overhead_key]
        return (f"Shipping to the UK and import duty from {ctx['region'].name}: {a.low:g}–{a.high:g}% of the "
                "factory cost above.")
    it = next(i for i in inputs.items if i.item_id == line["item_id"])
    extra = ctx.get("extras", {}).get(it.item_id)
    if extra is not None and extra.origin:
        qty = f"{it.quantity:g} × " if it.quantity != 1 else ""
        return f"{qty}{it.name} at {_money(A[it.cost_key])} each, needed by the {extra.origin}."
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
        "Ranges show the likely spread: each input varies within its range (widened for low confidence) and the effects are combined as independent.",
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
