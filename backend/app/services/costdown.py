"""Cost-down analysis: pricing targets, process routes per part, design-change scenarios,
the product-level optimum and the premium edition.

Everything is computed from a project Snapshot with `assemble()`, so nothing here
changes the project except `update_pricing` and `select_route` (which records an
engineering decision).
"""

from __future__ import annotations

import itertools
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.costing.assemble import CostConfig, ExtraItem, RouteChoice, Snapshot, assemble, route_changes_for
from app.costing.data import CostData, load_cost_data
from app.costing.model import CostInputs, crossover, evaluate, fixed_and_variable, part_quantities, total, unit_cost_range
from app.costing.pricing import PRICING_KEYS, STACK_KEYS, STACK_PCT_KEYS, assess, factory_targets, price_stack, targets
from app.models import EngineeringDecision, Part, Project
from app.rules.data import RuleSet, load_rules
from app.services.costing import reference_quantity, snapshot
from app.services.templates import load_template

SUMMARY_VOLUMES = [500, 2000]


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


def pricing_values(project: Project) -> tuple[dict[str, float], dict[str, Any]]:
    """Effective pricing assumptions (defaults overlaid with the user's edits) and per-key metadata."""
    cost = load_cost_data()
    tpl_pricing = load_template(project.template).get("pricing", {}) if project.template else {}
    req_retail = ((project.requirements or {}).get("target_retail_price") or {}).get("amount")
    retail = req_retail or tpl_pricing.get("retail_price")
    defaults: dict[str, float] = {
        "retail_price": retail or 0.0,
        "retail_low": tpl_pricing.get("retail_low", retail or 0.0),
        "retail_high": tpl_pricing.get("retail_high", retail or 0.0),
        "premium_retail": tpl_pricing.get("premium_retail", (retail or 0.0) * 1.4),
        **{k: v.value for k, v in cost.pricing.items()},
    }
    user = project.pricing or {}
    values = {k: float(user.get(k, defaults[k])) for k in PRICING_KEYS}
    meta = {}
    for k in PRICING_KEYS:
        seed = cost.pricing.get(k)
        meta[k] = {
            "value": values[k], "default": defaults[k], "edited": k in user,
            "source": "user" if k in user else (seed.source if seed else tpl_pricing.get("source", "template")),
            "confidence": seed.confidence if seed and k not in user else "high",
            "verified": bool(k in user) or (seed.verified if seed else True),
            "plain_language": seed.plain_language.strip() if seed else "",
        }
    return values, meta


def pricing_report(project: Project) -> dict[str, Any]:
    values, meta = pricing_values(project)
    return {"values": values, "meta": meta, "targets": targets(values) if values["retail_price"] else None}


def update_pricing(session: Session, project: Project, changes: dict[str, float]) -> dict[str, Any]:
    unknown = set(changes) - set(PRICING_KEYS)
    if unknown:
        raise HTTPException(422, f"Unknown pricing fields: {sorted(unknown)}")
    values, _ = pricing_values(project)
    new = {**values, **{k: float(v) for k, v in changes.items()}}
    for k in ("vat_rate", "dtc_factory_share", "retailer_margin", "wholesale_factory_share", "close_band"):
        if not 0 <= new[k] < 1:
            raise HTTPException(422, f"{k} must be between 0 and 1")
    if not 0 < new["retail_low"] <= new["retail_price"] <= new["retail_high"]:
        raise HTTPException(422, "Retail price must sit within its low–high range")
    for k in STACK_PCT_KEYS:
        if not 0 <= new[k] < 1:
            raise HTTPException(422, f"{k} must be between 0 and 1")
    for k in set(STACK_KEYS) - set(STACK_PCT_KEYS):
        if new[k] < 0:
            raise HTTPException(422, f"{k} can't be negative")
    if new["stack_returns_pct"] + new["stack_payment_pct"] * (1 + new["vat_rate"]) + new["stack_profit_pct"] >= 0.9:
        raise HTTPException(422, "Payment fees, returns and profit take 90% or more of the price")
    if new["premium_retail"] <= 0:
        raise HTTPException(422, "Premium retail price must be positive")
    project.pricing = {**(project.pricing or {}), **{k: float(v) for k, v in changes.items()}}
    if "retail_price" in changes:
        # Keep the requirement in step and mark it as the user's figure.
        req = dict(project.requirements or {})
        req["target_retail_price"] = {**(req.get("target_retail_price") or {"currency": "GBP"}), "amount": new["retail_price"]}
        project.requirements = req
        project.assumed_fields = [f for f in (project.assumed_fields or []) if f != "target_retail_price"]
    session.commit()
    return pricing_report(project)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _volumes(project: Project) -> list[int]:
    vols = list(load_cost_data().value("volume_table"))
    pv = (project.requirements or {}).get("production_volume")
    if pv and pv not in vols:
        vols.append(int(pv))
    return sorted(vols)


def _mid(inputs: CostInputs, q: float) -> float:
    return total(evaluate(inputs, inputs.mids(), q))


def _cost(snap: Snapshot, cfg: CostConfig, q: float, rules: RuleSet, cost: CostData) -> float:
    inputs, _ = assemble(snap, cfg, rules, cost)
    return _mid(inputs, q)


def _money(v: float) -> str:
    return f"£{v:,.2f}"


def _span(lo: float, hi: float) -> str:
    return _money(lo) if lo == hi else f"£{lo:,.0f}–£{hi:,.0f}"


# ---------------------------------------------------------------------------
# Process routes per part
# ---------------------------------------------------------------------------


def _part_sub_inputs(inputs: CostInputs, part_id: int) -> CostInputs:
    """Inputs for one part plus the extra items its route needs (per product)."""
    return CostInputs(
        assumptions=inputs.assumptions,
        parts=[p for p in inputs.parts if p.part_id == part_id],
        items=[i for i in inputs.items if i.part_id == part_id],
        spread=inputs.spread,
    )


def _route_tradeoffs(rules: RuleSet, cost: CostData, proc_key: str, mass_kg: float, extras: list[str],
                     delta_500: float | None, tooling: tuple[float, float]) -> dict[str, str]:
    proc = rules.processes[proc_key]
    rate = cost.process_rates[proc_key]
    finish_word = {"excellent": "an excellent", "good": "a good", "fair": "a fair", "poor": "a rough"}[proc.finish_quality]
    lt = rate.lead_time_weeks
    out = {
        "cost": ("Same cost as the current route." if delta_500 is None or abs(delta_500) < 0.005 else
                 f"{_money(abs(delta_500))} {'cheaper' if delta_500 < 0 else 'more'} per lamp at 500 units than the current route."),
        "finish": f"Gives {finish_word} surface as made. {proc.risks[0] if proc.risks else ''}".strip(),
        "weight": f"The part weighs about {mass_kg:.2f} kg" + (f"; adds {', '.join(extras)}." if extras else "."),
        "premium": {
            "excellent": "Keeps a premium, crisp finish.",
            "good": "Can look premium with normal finishing.",
            "fair": "Needs extra preparation to look premium under gloss lacquer.",
            "poor": "Needs machining and filling before it can look premium.",
        }[proc.finish_quality],
        "lead_time": f"About {lt.low:g}–{lt.high:g} weeks to tooling and first parts." if lt else "Lead time not known.",
        "tooling": ("No dedicated tooling: easy to change the design later." if tooling[1] == 0 else
                    f"One-off tooling {_span(*tooling)}" + (": a real commitment to this design." if tooling[1] >= 10000 else
                                                             ": cheap to change if the design moves.")),
    }
    return out


def part_routes(session: Session, project: Project, snap: Snapshot | None = None) -> dict[str, Any]:
    """Cost every viable process route for each manufactured part."""
    rules, cost = load_rules(), load_cost_data()
    snap = snap or snapshot(session, project)
    volumes = _volumes(project)
    base_inputs, base_ctx = assemble(snap, CostConfig(), rules, cost)
    costed_ids = {p.part_id for p in base_inputs.parts}
    out = []
    for sp in snap.parts:
        if sp.part_id not in costed_ids:
            continue
        candidates: list[tuple[str, str]] = []
        for v in sp.viable:
            pair = (v["process_key"], v["material_key"])
            if pair not in candidates and v["process_key"] in cost.process_rates and v["material_key"] in cost.material_prices:
                candidates.append(pair)
        current = (sp.process_key, sp.material_key)
        if current not in candidates:
            candidates.insert(0, current)
        viable_procs = {v["process_key"] for v in sp.viable}

        rows = []
        for proc_key, mat_key in candidates:
            cfg = CostConfig(routes={sp.cad_key: RouteChoice(proc_key, mat_key)})
            inputs, ctx = assemble(snap, cfg, rules, cost)
            sub = _part_sub_inputs(inputs, sp.part_id)
            spec = sub.parts[0]
            costs = {str(q): unit_cost_range(sub, q) for q in volumes}
            f, v = fixed_and_variable(sub)
            tool = inputs.assumptions[f"tooling:{sp.part_id}"]
            k = sub.keys_for_part(spec)
            mass = part_quantities(spec, k, sub.mids())["finished_kg"]
            extras = [f"{it.quantity:g} × {it.name.lower()}" for it in sub.items]
            changes = [d for d in ctx["design_changes"] if d["part_id"] == sp.part_id]
            rows.append({
                "process_key": proc_key, "process": spec.process_name, "material_key": mat_key, "material": spec.material_name,
                "is_current": (proc_key, mat_key) == current, "viable": proc_key in viable_procs,
                "costs": costs, "tooling": {"low": tool.low, "high": tool.high}, "fixed": round(f, 2), "per_unit": round(v, 2),
                "design_changes": [d["text"] for d in changes],
                "extra_items": extras,
                "flags": [fl for fl in ctx["flags"] if fl["part"] == sp.name],
                "mass_kg": round(mass, 3),
                "_fv": (f, v),
            })

        cur = next(r for r in rows if r["is_current"])
        for r in rows:
            d500 = r["costs"]["500"]["mid"] - cur["costs"]["500"]["mid"] if "500" in r["costs"] else None
            r["tradeoffs"] = _route_tradeoffs(rules, cost, r["process_key"], r["mass_kg"], r["extra_items"], d500,
                                              (r["tooling"]["low"], r["tooling"]["high"]))
            r["crossovers"] = []
            for other in rows:
                if other is r:
                    continue
                q = crossover(r["_fv"], other["_fv"])
                if q is None:
                    continue
                cheaper_above = r["_fv"][1] < other["_fv"][1]  # lower per-unit cost wins above the crossover
                r["crossovers"].append({
                    "vs": other["process"], "vs_material": other["material"], "quantity": round(q),
                    "text": f"{'Cheaper' if cheaper_above else 'Dearer'} than {other['process'].lower()} above about {q:,.0f} units.",
                })
        for r in rows:
            r.pop("_fv")
        cheapest = {str(q): min(rows, key=lambda r: r["costs"][str(q)]["mid"])["process"] for q in volumes}
        out.append({"part_id": sp.part_id, "name": sp.name, "cad_key": sp.cad_key, "current": cur["process"],
                    "routes": sorted(rows, key=lambda r: r["costs"][str(volumes[1] if len(volumes) > 1 else volumes[0])]["mid"]),
                    "cheapest_by_volume": cheapest})
    return {"volumes": volumes, "parts": out}


def select_route(session: Session, project: Project, part: Part, process_key: str, material_key: str, reason: str) -> dict[str, Any]:
    """Choose a process route for a part: records an engineering decision and updates the part.

    CAD is not changed. If the route needs a design change, the decision is flagged so the
    BOM and DFM report show that the CAD no longer matches.
    """
    rules, cost = load_rules(), load_cost_data()
    if not reason.strip():
        raise HTTPException(422, "Give a reason for the decision")
    if process_key not in rules.processes or process_key not in cost.process_rates:
        raise HTTPException(422, f"Unknown or uncosted process {process_key!r}")
    snap = snapshot(session, project)
    sp = next((p for p in snap.parts if p.part_id == part.id), None)
    if sp is None:
        raise HTTPException(404, "Part not found")
    viable = {(v["process_key"], v["material_key"]) for v in sp.viable} | {(sp.process_key, sp.material_key)}
    if (process_key, material_key) not in viable:
        raise HTTPException(422, "That route is not one the rules engine considers viable for this part")
    proc, mat = rules.processes[process_key], rules.materials.get(material_key)
    if mat is None:
        raise HTTPException(422, f"Unknown material {material_key!r}")

    from app.services.decisions import route_decision_chosen

    recommended = next((v for v in sp.viable), None)
    is_recommended = bool(recommended) and (recommended["process_key"], recommended["material_key"]) == (process_key, material_key)
    chosen = route_decision_chosen(project, part, process_key, material_key,
                                   part.process or (sp.process_key or ""), part.material or (sp.material_key or ""))
    decision = EngineeringDecision(
        project_id=project.id, part_id=part.id, topic="process_route",
        status="accepted" if is_recommended else "edited",
        recommendation={"recommendation": {"process_key": recommended["process_key"], "process_name": recommended["process_name"],
                                           "material_key": recommended["material_key"], "material_name": recommended["material_name"]}}
        if recommended else {},
        chosen=chosen,
        note=reason.strip(),
    )
    part.process = proc.name
    part.material = mat.name
    session.add(decision)
    session.commit()
    return {"decision_id": decision.id, "status": decision.status, "chosen": decision.chosen, "note": decision.note}


def cad_mismatches(project: Project) -> list[dict[str, Any]]:
    """Parts whose latest route decision needs a design change the CAD doesn't show yet."""
    latest: dict[int, EngineeringDecision] = {}
    for d in sorted(project.decisions, key=lambda d: (d.created_at, d.id)):
        if d.topic == "process_route" and d.part_id is not None:
            latest[d.part_id] = d
    from app.services.decisions import unimplemented_changes

    parts = {p.id: p for p in project.parts}
    out = []
    for pid, d in latest.items():
        part = parts.get(pid)
        keys = d.chosen.get("design_change_keys")
        if keys is None:  # decisions recorded before change keys were stored
            mismatch = bool(d.chosen.get("cad_mismatch"))
            texts = d.chosen.get("design_changes", [])
        else:
            missing = unimplemented_changes(project, part.cad_key if part else None, keys)
            mismatch = bool(missing)
            texts = [t for k, t in zip(keys, d.chosen.get("design_changes", [])) if k in missing]
        if mismatch:
            out.append({"part_id": pid, "part": part.name if part else "?", "process": d.chosen.get("process"), "changes": texts})
    return out


# ---------------------------------------------------------------------------
# Design-change scenarios
# ---------------------------------------------------------------------------


def scenario_defs(project: Project) -> list[dict[str, Any]]:
    return load_template(project.template).get("scenarios", []) if project.template else []


def change_config(defn: dict[str, Any], option: int, params: dict[str, Any]) -> CostConfig:
    eff = defn.get("effect", {})
    cfg = CostConfig()
    if "reroute" in eff:
        opt = eff["reroute"]["options"][option]
        cfg.routes[eff["reroute"]["part"]] = RouteChoice(opt["process"], opt["material"], opt.get("tooling"), opt.get("label", ""))
    for rr in eff.get("reroutes", []):
        cfg.routes[rr["part"]] = RouteChoice(rr["process"], rr["material"], rr.get("tooling"), defn.get("label", ""))
    cfg.finish_overrides.update(eff.get("finishes", {}))
    if "remove_part" in eff:
        rp = eff["remove_part"]
        cfg.removed_parts |= set(rp if isinstance(rp, list) else [rp])
    for it in eff.get("add_items", []):
        qty = float(params.get(it["quantity_param"], 1)) if it.get("quantity_param") else float(it.get("quantity", 1))
        cfg.add_items.append(ExtraItem(it["price_key"], qty, kind=it.get("kind", "bought_in"), origin=f"scenario {defn['letter']}"))
    cfg.remove_price_keys |= set(eff.get("remove_items", []))
    cfg.replace_price_keys.update(eff.get("replace_items", {}))
    if "assembly_min" in eff:
        cfg.assembly_delta_min = (float(eff["assembly_min"]["low"]), float(eff["assembly_min"]["high"]))
    if "scale_height" in eff:
        cfg.height_mm = float(eff["scale_height"])
    return cfg


def option_allowed(defn: dict[str, Any], option: int, snap: Snapshot, rules: RuleSet) -> tuple[bool, str]:
    """Whether a scenario option respects the design constraints (e.g. no plastic on visible parts)."""
    from app.rules.engine import material_allowed
    from app.rules.match import match_finishes

    eff = defn.get("effect", {})
    checks: list[tuple[str, str]] = []
    if eff.get("reroute"):
        checks.append((eff["reroute"]["part"], eff["reroute"]["options"][option]["material"]))
    checks += [(rr["part"], rr["material"]) for rr in eff.get("reroutes", [])]
    for cad_key, material in checks:
        sp = next((s for s in snap.parts if s.cad_key == cad_key), None)
        if sp is None:
            continue
        traits = set(sp.traits) | set(sp.derived_traits)
        override = eff.get("finishes", {}).get(cad_key)
        finishes = [override] if override else match_finishes(rules, sp.finish_text)
        for fk in finishes or [None]:
            ok, why = material_allowed(rules, traits, sp.material_category, material, fk)
            if not ok:
                return False, why
    return True, ""


def n_options(defn: dict[str, Any]) -> int:
    return len(defn.get("effect", {}).get("reroute", {}).get("options", [])) or 1


def selection_config(defs: dict[str, dict[str, Any]], selection: list[tuple[str, int]], region: str,
                     params: dict[str, Any]) -> CostConfig:
    cfg = CostConfig(region=region)
    for key, opt in selection:
        cfg = cfg.merged(change_config(defs[key], opt, params))
    cfg.region = region
    return cfg


def _conflict(keys: tuple[str, ...], defs: dict[str, dict[str, Any]]) -> bool:
    ks = set(keys)
    return any(c in ks for k in keys for c in defs[k].get("conflicts", []))


def _cheapest_options(snap: Snapshot, defs: dict[str, dict[str, Any]], region: str, q: float, rules: RuleSet,
                      cost: CostData) -> dict[str, int | None]:
    """Cheapest allowed option for each change, judged on its own (options touch only their own part).

    None means every option of that change breaks a design constraint, so the optimiser skips it.
    """
    best: dict[str, int | None] = {}
    for key, d in defs.items():
        allowed = [i for i in range(n_options(d)) if option_allowed(d, i, snap, rules)[0]]
        if len(allowed) <= 1:
            best[key] = allowed[0] if allowed else None
            continue
        costs = {i: _cost(snap, selection_config(defs, [(key, i)], region, snap.params), q, rules, cost) for i in allowed}
        best[key] = min(allowed, key=lambda i: costs[i])
    return best


def resolve(selection: list[dict[str, Any]], defs: dict[str, dict[str, Any]], snap: Snapshot, region: str, q: float,
            rules: RuleSet, cost: CostData) -> list[tuple[str, int]]:
    """Turn [{key, option|None}] into concrete (key, option) pairs; None picks the cheapest option."""
    cheapest = None
    out = []
    for s in selection:
        if s["key"] not in defs:
            raise HTTPException(422, f"Unknown scenario {s['key']!r}")
        opt = s.get("option")
        if opt is None:
            if cheapest is None:
                cheapest = _cheapest_options(snap, defs, region, q, rules, cost)
            opt = cheapest[s["key"]]
            if opt is None:
                raise HTTPException(422, f"Scenario {s['key']}: every option breaks a design constraint")
        if not 0 <= opt < n_options(defs[s["key"]]):
            raise HTTPException(422, f"Scenario {s['key']} has no option {opt}")
        ok, why = option_allowed(defs[s["key"]], int(opt), snap, rules)
        if not ok:
            raise HTTPException(422, f"Scenario {s['key']} option {opt} is excluded: {why}")
        out.append((s["key"], int(opt)))
    keys = tuple(k for k, _ in out)
    if _conflict(keys, defs):
        raise HTTPException(422, "These scenarios conflict with each other")
    return out


# Which premium impacts each optimisation tier may accept.
TIERS = {
    "strict": {"none"},  # no compromise to look and feel
    "premium": {"none", "slight"},  # slight compromises (e.g. painted stripe, adapter) allowed
    "any": {"none", "slight", "significant"},
}


def optimise(snap: Snapshot, defs: dict[str, dict[str, Any]], q: float, rules: RuleSet, cost: CostData,
             tier: str = "any", forbid: set[str] | None = None, extra: CostConfig | None = None) -> dict[str, Any]:
    """Cheapest combination of changes and region at quantity q (exhaustive over subsets and regions)."""
    forbid = forbid or set()
    allowed = TIERS[tier]
    keys = [k for k, d in defs.items()
            if k not in forbid and not d.get("edition") and d.get("premium_impact", "none") in allowed]
    best: dict[str, Any] | None = None
    for region in cost.regions:
        options = _cheapest_options(snap, {k: defs[k] for k in keys}, region, q, rules, cost)
        usable = [k for k in keys if options[k] is not None]
        for r in range(len(usable) + 1):
            for combo in itertools.combinations(usable, r):
                if _conflict(combo, defs):
                    continue
                sel = [(k, options[k]) for k in combo]
                cfg = selection_config(defs, sel, region, snap.params)
                if extra is not None:
                    cfg = cfg.merged(extra)
                    cfg.region = region
                c = _cost(snap, cfg, q, rules, cost)
                if best is None or c < best["mid"] - 1e-9:
                    best = {"mid": c, "selection": sel, "region": region}
    assert best is not None
    return best


def _rerouted_parts(defn: dict[str, Any]) -> list[str]:
    eff = defn.get("effect", {})
    return ([eff["reroute"]["part"]] if "reroute" in eff else []) + [rr["part"] for rr in eff.get("reroutes", [])]


def describe_selection(defs: dict[str, dict[str, Any]], selection: list[tuple[str, int]]) -> list[dict[str, Any]]:
    out = []
    for key, opt in selection:
        d = defs[key]
        options = d.get("effect", {}).get("reroute", {}).get("options", [])
        out.append({"key": key, "letter": d["letter"], "label": d["label"], "option": opt,
                    "option_label": options[opt]["label"] if options else "", "premium_impact": d.get("premium_impact", "none")})
    return out


def _config_flags(defs: dict[str, dict[str, Any]], selection: list[tuple[str, int]], ctx: dict[str, Any]) -> list[dict[str, str]]:
    flags = [dict(fl, scenario=defs[k]["letter"]) for k, _ in selection for fl in defs[k].get("flags", [])]
    # A scenario that reroutes a part and carries its own safety flag already covers the
    # route-change safety flag for that part, so don't repeat it.
    covered = {
        part for k, _ in selection if any(f.get("kind") == "safety" for f in defs[k].get("flags", []))
        for part in _rerouted_parts(defs[k])
    }
    for fl in ctx["flags"]:
        if fl["kind"] == "safety" and ctx["part_keys"].get(fl.get("part")) in covered:
            continue
        if not any(fl["message"] == f["message"] for f in flags):
            flags.append(fl)
    if ctx["region"].key != "uk":
        flags.append({"kind": "region", "message": f"{ctx['region'].name}: {ctx['region'].lead_time_note}"})
    return flags


def evaluate_selection(session: Session, project: Project, selection: list[dict[str, Any]], region: str) -> dict[str, Any]:
    """Cost of a chosen set of changes and region, with each change's marginal impact and target status."""
    rules, cost = load_rules(), load_cost_data()
    if region not in cost.regions:
        raise HTTPException(422, f"Unknown region {region!r}")
    snap = snapshot(session, project)
    defs = {d["key"]: d for d in scenario_defs(project)}
    ref_q, _ = reference_quantity(project)
    sel = resolve(selection, defs, snap, region, ref_q, rules, cost)
    cfg = selection_config(defs, sel, region, snap.params)
    inputs, ctx = assemble(snap, cfg, rules, cost)
    base_inputs, _ = assemble(snap, CostConfig(), rules, cost)
    values, _ = pricing_values(project)
    tg = targets(values) if values["retail_price"] else None

    volumes = _volumes(project)
    by_q = []
    for q in volumes:
        r = unit_cost_range(inputs, q)
        r["current_mid"] = round(_mid(base_inputs, q), 2)
        r["saving"] = round(r["current_mid"] - r["mid"], 2)
        if tg:
            r["targets"] = assess(r["mid"], tg["standard"], values["close_band"])
        by_q.append(r)

    marginal = []
    for key, opt in sel:
        without = [(k, o) for k, o in sel if k != key]
        cfg_wo = selection_config(defs, without, region, snap.params)
        m = {}
        for q in SUMMARY_VOLUMES:
            m[str(q)] = round(_cost(snap, cfg_wo, q, rules, cost) - _mid(inputs, q), 2)
        marginal.append({**describe_selection(defs, [(key, opt)])[0], "saving": m})
    if region != "uk":
        cfg_uk = selection_config(defs, sel, "uk", snap.params)
        marginal.append({"key": "region", "letter": "i", "label": f"Make in {cost.regions[region].name}", "option": None,
                         "option_label": "", "premium_impact": "none",
                         "saving": {str(q): round(_cost(snap, cfg_uk, q, rules, cost) - _mid(inputs, q), 2) for q in SUMMARY_VOLUMES}})
    return {
        "selection": describe_selection(defs, sel), "region": region, "volumes": by_q, "marginal": marginal,
        "flags": _config_flags(defs, sel, ctx), "design_changes": ctx["design_changes"],
        "removed": [s["name"] for s in ctx["skipped"] if "Removed" in s["reason"]],
    }


def scenario_catalog(session: Session, project: Project) -> dict[str, Any]:
    """Each change on its own (every option) and each region: saving vs the current configuration."""
    rules, cost = load_rules(), load_cost_data()
    snap = snapshot(session, project)
    defs = scenario_defs(project)
    base = {q: _cost(snap, CostConfig(), q, rules, cost) for q in SUMMARY_VOLUMES}
    out = []
    for d in defs:
        opts = []
        for i in range(n_options(d)):
            cfg = change_config(d, i, snap.params)
            label = d.get("effect", {}).get("reroute", {}).get("options", [{}])[i].get("label", "") if n_options(d) > 1 or "reroute" in d.get("effect", {}) else ""
            ok, why = option_allowed(d, i, snap, rules)
            opts.append({"option": i, "label": label, "allowed": ok, "excluded_reason": why,
                         "saving": {str(q): round(base[q] - _cost(snap, cfg, q, rules, cost), 2) for q in SUMMARY_VOLUMES}})
        out.append({
            "key": d["key"], "letter": d["letter"], "label": d["label"], "design_change": " ".join(d.get("design_change", "").split()),
            "premium_impact": d.get("premium_impact", "none"), "conflicts": d.get("conflicts", []), "flags": d.get("flags", []),
            "tradeoffs": d.get("tradeoffs", {}), "options": opts,
        })
    regions = [{
        "key": r.key, "name": r.name, "lead_time_note": r.lead_time_note, "verified": r.verified, "confidence": r.confidence,
        "multipliers": {"machine": [r.machine.low, r.machine.high], "labour": [r.labour.low, r.labour.high],
                        "tooling": [r.tooling.low, r.tooling.high], "finishing": [r.finishing.low, r.finishing.high],
                        "freight_duty_pct": [r.freight_duty_pct.low, r.freight_duty_pct.high]},
        "saving": {str(q): round(base[q] - _cost(snap, CostConfig(region=r.key), q, rules, cost), 2) for q in SUMMARY_VOLUMES},
    } for r in cost.regions.values()]
    return {"scenarios": out, "regions": regions, "current": {str(q): round(v, 2) for q, v in base.items()}}


# ---------------------------------------------------------------------------
# Product-level view
# ---------------------------------------------------------------------------


def power_options(project: Project, defs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Power options to cost side by side (template `power_options`); a single default if none."""
    opts = load_template(project.template).get("power_options") if project.template else None
    if not opts:
        return [{"key": "A", "label": "Current electronics", "scenario": None}]
    return [o for o in opts if not o.get("scenario") or o["scenario"] in defs]


def edition_config(project: Project, option_key: str, removed: set[str]) -> CostConfig:
    ed = load_template(project.template).get("premium_edition", {})
    opt = next(o for o in ed["options"] if o["key"] == option_key)
    fin = load_rules().finishes.get(opt.get("finish") or "")
    if fin is not None and fin.metal_effect:
        raise HTTPException(422, f"Premium edition option {option_key!r} uses a metal-effect finish, which the design constraint forbids")
    cfg = CostConfig()
    for cad_key in ed["parts"]:
        if cad_key in removed:
            continue
        if opt.get("material"):
            cfg.material_overrides[cad_key] = opt["material"]
        if opt.get("finish"):
            cfg.finish_overrides[cad_key] = opt["finish"]
    return cfg


def price_points(project: Project) -> list[float]:
    """Retail prices (inc. VAT) to compare side by side: the template's list plus the planned price."""
    tpl = load_template(project.template).get("pricing", {}) if project.template else {}
    values, _ = pricing_values(project)
    pts = {float(x) for x in tpl.get("price_points", [])}
    if values["retail_price"]:
        pts.add(float(values["retail_price"]))
    return sorted(pts)


def price_point_table(project: Project, rows: list[dict[str, Any]], values: dict[str, float]) -> dict[str, Any]:
    """Current and best configurations (first power option) against the DTC and retail-channel targets at each
    retail price point."""
    pts = price_points(project)
    close = values["close_band"]
    points = [factory_targets(rp, values) for rp in pts]
    first_power = rows[0]["power"] if rows else None
    out = []
    for r in rows:
        if r["power"] != first_power or r["tier"] not in ("current", "strict", "premium", "any") or r.get("same_as"):
            continue
        mid = r["cost"]["mid"]
        out.append({
            "quantity": r["quantity"], "label": r["label"], "tier": r["tier"], "region_name": r["region_name"],
            "selection": [s["label"] + (f" ({s['option_label']})" if s["option_label"] else "") for s in r["selection"]],
            "cost": {"low": r["cost"]["low"], "mid": mid, "high": r["cost"]["high"]},
            "by_price": {f"{pt['retail_inc_vat']:g}": assess(mid, pt, close) for pt in points},
        })
    return {"points": points, "rows": out, "power_label": rows[0]["power_label"] if rows else "",
            "notes": ["DTC target = ex-VAT price × DTC factory share; retail-channel target = ex-VAT price × (1 − retailer "
                      "margin) × wholesale factory share (Pricing panel above).",
                      "Status compares the midpoint estimate with each target: pass at or under, close within "
                      f"{close:.0%} over, fail beyond."]}


def product_summary(session: Session, project: Project) -> dict[str, Any]:
    """Current configuration vs best combinations at 500 and 2,000 units, against both cost targets,
    plus the premium brass edition."""
    rules, cost = load_rules(), load_cost_data()
    snap = snapshot(session, project)
    defs = {d["key"]: d for d in scenario_defs(project)}
    values, _ = pricing_values(project)
    if not values["retail_price"]:
        raise HTTPException(409, "Set a target retail price first")
    tg = targets(values)
    close = values["close_band"]

    def row(label: str, sel: list[tuple[str, int]], region: str, q: int, extra: CostConfig | None = None,
            target_set: dict[str, float] | None = None) -> dict[str, Any]:
        cfg = selection_config(defs, sel, region, snap.params)
        if extra is not None:
            cfg = cfg.merged(extra)
            cfg.region = region
        inputs, ctx = assemble(snap, cfg, rules, cost)
        r = unit_cost_range(inputs, q)
        return {
            "label": label, "quantity": q, "region": region, "region_name": cost.regions[region].name,
            "selection": describe_selection(defs, sel), "cost": r,
            "targets": assess(r["mid"], target_set or tg["standard"], close),
            "flags": _config_flags(defs, sel, ctx),
        }

    rows = []
    premium_rows = []
    editions: list[dict[str, Any]] = []
    simplified = next((k for k, d in defs.items() if d.get("edition")), None)
    tier_labels = [
        ("strict", "Best with no compromise to look and feel"),
        ("premium", "Best allowing slight compromises"),
        ("any", "Lowest cost (any change)"),
    ]
    powers = power_options(project, defs)
    for power in powers:
        forced = [(power["scenario"], 0)] if power["scenario"] else []
        forbid = {p["scenario"] for p in powers if p["scenario"]}
        extra = selection_config(defs, forced, "uk", snap.params) if forced else None
        for q in SUMMARY_VOLUMES:
            rows.append(row("Current configuration", forced, "uk", q) | {"tier": "current", "power": power["key"],
                                                                         "power_label": power["label"]})
            seen: list[tuple[Any, str]] = []
            for tier, label in tier_labels:
                best = optimise(snap, defs, q, rules, cost, tier=tier, forbid=forbid, extra=extra)
                sel = forced + best["selection"]
                key = (tuple(sel), best["region"])
                same_as = next((lbl for k, lbl in seen if k == key), None)
                seen.append((key, label))
                rows.append(row(label, sel, best["region"], q) | {"tier": tier, "same_as": same_as, "power": power["key"],
                                                                 "power_label": power["label"]})
            if simplified:
                s_forced = forced + [(simplified, 0)]
                s_extra = selection_config(defs, s_forced, "uk", snap.params)
                best = optimise(snap, defs, q, rules, cost, tier="strict", forbid=forbid | {simplified}, extra=s_extra)
                full = next(r for r in rows if r["tier"] == "strict" and r["power"] == power["key"] and r["quantity"] == q)
                simple = row(defs[simplified]["label"], s_forced + best["selection"], best["region"], q)
                for label, r in (("Full detail", full), ("Simplified premium", simple)):
                    editions.append({
                        "edition": label, "power": power["key"], "power_label": power["label"], "quantity": q,
                        "region_name": r["region_name"], "cost": r["cost"], "targets": r["targets"],
                        "selection": [x["label"] + (f" ({x['option_label']})" if x["option_label"] else "")
                                      for x in r["selection"]],
                        "price_stack": price_stack(r["cost"]["mid"], q, values),
                    })
            for opt in [o["key"] for o in load_template(project.template).get("premium_edition", {}).get("options", [])]:
                ed_cur = edition_config(project, opt, set())
                ed_extra = ed_cur.merged(extra) if extra is not None else ed_cur
                premium_rows.append(row(f"Brass edition ({opt}), current configuration", forced, "uk", q, ed_cur,
                                        tg["premium"]) | {"power": power["key"], "power_label": power["label"]})
                be = optimise(snap, defs, q, rules, cost, tier="strict", forbid=forbid, extra=ed_extra)
                premium_rows.append(row(f"Brass edition ({opt}), best with no compromise", forced + be["selection"],
                                        be["region"], q, ed_cur, tg["premium"]) | {"power": power["key"],
                                                                                    "power_label": power["label"]})
    ed = load_template(project.template).get("premium_edition", {})
    return {
        "targets": tg, "close_band": close, "rows": rows, "power_options": powers,
        "price_points": price_point_table(project, rows, values),
        "editions": {
            "rows": editions,
            "label": defs[simplified]["label"] if simplified else None,
            "notes": [
                "Full detail is the best configuration with no compromise to look and feel; simplified premium is the same "
                "search with the gallery, railing and lantern frame in colour-matched lacquered aluminium.",
                "Break-even retail covers factory cost and every DTC line with no profit; target retail adds the profit "
                "target. Both include VAT. Edit the lines in the Price stack card.",
            ],
        },
        "premium": {"label": ed.get("label", "Premium edition"), "retail": values["premium_retail"],
                    "targets": tg["premium"], "rows": premium_rows,
                    "options": {o["key"]: o["label"] for o in ed.get("options", [])}},
        "notes": [
            "Status compares the midpoint estimate with each target: pass at or under, close within "
            f"{close:.0%} over, fail beyond.",
            "Best combinations search every combination of changes and every region; multi-option changes use their cheapest option.",
            *load_template(project.template).get("cost_down_notes", []),
            "Changes whose options break a design constraint (e.g. plastic on a visible part) are never chosen.",
            "Rates are unverified: most are model-generated, some come from published distributor prices. Treat the ranking as a guide for which quotes to get first.",
        ],
    }

