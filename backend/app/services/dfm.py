"""Basic DFM (design for manufacture) report.

Combines CAD parameter checks, rules-engine recommendations and project
state into one report. Every check has a level: pass | info | warning | fail.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.cad import faro
from app.models import Project
from app.rules.data import load_rules
from app.rules.match import match_process
from app.schemas import Requirements
from app.services.cad import current_parameters, latest_model, validate
from app.services.recommendations import open_project_decisions, project_recommendations

REQ_LABELS = {
    "approx_dimensions": "Approximate dimensions",
    "target_retail_price": "Target retail price",
    "production_volume": "Production volume",
    "target_unit_cost": "Target unit cost",
    "intended_markets": "Intended markets",
    "power_type": "Power type",
}


def _check(area: str, level: str, title: str, detail: str, unverified: bool = False, part: str | None = None) -> dict[str, Any]:
    return {"area": area, "level": level, "title": title, "detail": detail, "unverified": unverified, "part": part}


def _effective(part, rec, rules):
    """Process key in effect for a part: the user's choice if set, else the recommendation."""
    if part.process:
        key = match_process(rules, part.process)
        return key, "decided"
    r = rec.get("recommendation") or {}
    return r.get("process_key"), "recommended"


def build_dfm(project: Project) -> dict[str, Any]:
    rules = load_rules()
    recs = {r["part_id"]: r for r in project_recommendations(project)}
    req = Requirements.model_validate(project.requirements or {})
    checks: list[dict[str, Any]] = []

    # --- Project-level inputs ---------------------------------------------
    if req.production_volume is None:
        checks.append(_check("Project", "warning", "Production volume not set",
                             f"Process choices assume about {rules.plan('assumed_volume_when_unknown')} units. "
                             "Several parts change process at higher volume.", unverified=True))
    for od in open_project_decisions(project):
        if od["open"]:
            checks.append(_check("Project", "warning", f"Open decision: {od['question']}", " ".join(od["impact"].split())))
    if req.target_unit_cost.amount is None:
        checks.append(_check("Project", "info", "Target unit cost not set", "Cost can't be checked against a target yet."))

    # --- Geometry checks from CAD parameters -------------------------------
    params: dict[str, Any] = {}
    latest = latest_model(project)
    if project.template == "faro":
        params = current_parameters(project)
        result = validate(project, params)
        for e in result.errors:
            checks.append(_check("Geometry", "fail", "Invalid CAD parameter", e.message, "unverified" in e.message))
        for w in result.warnings:
            checks.append(_check("Geometry", "warning", "CAD parameter warning", w.message, "unverified" in w.message))
        if latest is None:
            checks.append(_check("Geometry", "info", "No CAD generated yet", "Generate CAD to check the solids."))
        else:
            bad = [k for k, i in latest.part_info.items() if not i.get("valid", True)]
            if bad:
                checks.append(_check("Geometry", "fail", "Invalid solids", f"Kernel reports invalid geometry: {', '.join(bad)}"))
            else:
                checks.append(_check("Geometry", "pass", f"CAD v{latest.version} solids valid",
                                     f"{len(latest.part_info)} parts generated, one body each."))

        p = {k: float(v) for k, v in params.items()}
        ratio = p["base_diameter"] / p["overall_height"]
        min_ratio = rules.plan("min_stability_ratio")
        checks.append(_check(
            "Geometry", "pass" if ratio >= min_ratio else "warning", "Stability (heuristic)",
            f"Base diameter is {ratio:.0%} of overall height (heuristic minimum {min_ratio:.0%}). "
            "The real requirement is a tilt test on the finished lamp.", unverified=True, part="Base"))

        clearance = faro.led_clearance(params)
        min_clear = rules.plan("min_led_to_lantern_clearance_mm")
        checks.append(_check(
            "Thermal", "pass" if clearance >= min_clear else "warning", "LED to lantern clearance",
            f"About {clearance:.0f} mm between the LED and the lantern wall (heuristic minimum {min_clear} mm). "
            "Confirm temperatures by test once the LED is chosen.", unverified=True, part="Lantern"))

        min_hole = rules.plan("min_cable_hole_mm")
        checks.append(_check(
            "Electrical", "pass" if p["cable_hole_diameter"] >= min_hole else "warning", "Cable entry hole size",
            f"Cable hole is {p['cable_hole_diameter']:g} mm (heuristic minimum {min_hole} mm for a mains flex plus grommet).",
            unverified=True, part="Cable / power entry"))

        checks.append(_check(
            "Assembly", "pass", "Central lamp tube construction",
            "One M10x1 lamp tube clamps base, body, LED plate, glass and cap; no threads are cut in thin walls. "
            f"The weight plate is screwed to {int(p['mounting_hole_count'])} rivet nuts in the base so it can't turn or rattle.",
            unverified=True, part="Base"))

        from app.services.cad import mass_estimate

        mass = mass_estimate(project)
        if mass and mass["target_kg"]:
            level = {"ok": "pass", "low": "warning", "high": "warning"}.get(mass["status"], "info")
            hint = {"low": " Increase the weight plate thickness or diameter.", "high": " Lighter than this may be fine; check the target."}
            checks.append(_check(
                "Geometry", level, "Lamp mass vs target",
                f"Estimated {mass['total_kg']:.2f} kg vs target {mass['target_kg']:.2f} kg "
                f"(weight plate {mass['parts_kg'].get('weight_plate', 0):.2f} kg).{hint.get(mass['status'], '')}",
                unverified=True, part="Weight plate"))

    # --- Chosen process routes that the CAD doesn't reflect yet ------------
    from app.services.costdown import cad_mismatches

    for m in cad_mismatches(project):
        checks.append(_check("Process", "warning", f"{m['part']}: CAD does not match the chosen route",
                             f"{m['process']} needs: " + " ".join(m["changes"]) + " Update the CAD before quoting.",
                             unverified=True, part=m["part"]))

    # --- Per-part checks ----------------------------------------------------
    parts_out = []
    for part in project.parts:
        rec = recs.get(part.id, {})
        proc_key, basis = _effective(part, rec, rules)
        proc = rules.processes.get(proc_key) if proc_key else None
        name = part.name

        if proc is None:
            checks.append(_check("Process", "warning", f"{name}: no process", "Set or accept a process for this part.", part=name))
        elif params and part.cad_key in ("main_body", "lantern", "base") and proc.wall_mm:
            wall = float(params["lantern_wall_thickness" if part.cad_key == "lantern" else "wall_thickness"])
            w = proc.wall_mm
            if not w.min <= wall <= w.max:
                level = "fail"
            elif not w.typical_min <= wall <= w.typical_max:
                level = "warning"
            else:
                level = "pass"
            checks.append(_check("Process", level, f"{name}: wall thickness for {proc.name.lower()}",
                                 f"{wall:g} mm vs typical {w.typical_min:g}–{w.typical_max:g} mm (possible {w.min:g}–{w.max:g}).",
                                 not proc.verified, part=name))

        draft = rules.draft_angles.get(proc_key or "")
        if draft and params:
            if part.cad_key == "main_body":
                taper = faro.body_taper_deg(params)
                ok = taper >= draft.external_deg
                checks.append(_check("Process", "pass" if ok else "warning", f"{name}: draft / taper",
                                     f"Body taper is {taper:.1f}° vs {draft.external_deg:g}° needed for {proc.name.lower()}.",
                                     not draft.verified, part=name))
            elif part.cad_key in ("base", "top_cap", "band"):
                checks.append(_check("Process", "warning", f"{name}: no draft in CAD",
                                     f"The CAD model has vertical walls; {proc.name.lower()} needs about "
                                     f"{draft.external_deg:g}° external / {draft.internal_deg:g}° internal draft.",
                                     not draft.verified, part=name))

        parts_out.append({
            "part_id": part.id,
            "name": name,
            "process": proc.name if proc else part.process or "",
            "material": part.material or (rec.get("recommendation") or {}).get("material_name", ""),
            "basis": basis,
            "decision": (rec.get("decision") or {}).get("status"),
            "confidence": rec.get("confidence"),
            "risks": rec.get("risks", []),
            "safety_flags": rec.get("safety_flags", []),
            "open_questions": rec.get("open_questions", []),
            "uses_unverified_data": rec.get("uses_unverified_data", False),
        })

    safety = []
    for po in parts_out:
        for f in po["safety_flags"]:
            safety.append({"part": po["name"], **f})

    questions = []
    for po in parts_out:
        for q in po["open_questions"]:
            questions.append({"part": po["name"], "question": q})

    assumptions = [f"{REQ_LABELS.get(f, f)} is a placeholder / assumption." for f in project.assumed_fields]
    if params:
        assumptions.append("CAD dimensions are placeholders until Faro's real size is set.")
    assumptions.append("All rule data is model-generated and unverified unless marked otherwise.")

    counts = {lvl: sum(1 for c in checks if c["level"] == lvl) for lvl in ("fail", "warning", "info", "pass")}
    return {
        "project": project.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cad_version": latest.version if latest else None,
        "summary": {
            **counts,
            "safety_items": len(safety),
            "open_questions": len(questions),
            "unverified_checks": sum(1 for c in checks if c["unverified"]),
        },
        "checks": checks,
        "parts": parts_out,
        "safety": safety,
        "open_questions": questions,
        "assumptions": assumptions,
        "disclaimer": (
            "Engineering guidance only. Based on unverified, model-generated rules. Not a substitute for "
            "manufacturer review or certified testing; it does not establish legal compliance."
        ),
    }


def dfm_markdown(project: Project) -> str:
    r = build_dfm(project)
    s = r["summary"]
    lines = [
        f"# DFM report: {r['project']}",
        "",
        f"Generated {r['generated_at'][:16].replace('T', ' ')} UTC"
        + (f" · CAD v{r['cad_version']}" if r["cad_version"] else " · no CAD generated"),
        "",
        f"> {r['disclaimer']}",
        "",
        f"**Summary:** {s['fail']} fail, {s['warning']} warnings, {s['info']} info, {s['pass']} pass · "
        f"{s['safety_items']} safety items · {s['open_questions']} open questions",
        "",
        "## Checks",
        "",
        "| Level | Area | Check | Detail |",
        "|---|---|---|---|",
    ]
    for c in r["checks"]:
        flag = " (unverified data)" if c["unverified"] else ""
        lines.append(f"| {c['level'].upper()} | {c['area']} | {c['title']} | {c['detail']}{flag} |")
    lines += ["", "## Safety items (verify with a qualified person or manufacturer)", ""]
    lines += [f"- **{x['part']}:** {x['message']} _Verify with: {x['verify_with']}._" for x in r["safety"]] or ["- None"]
    lines += ["", "## Parts", ""]
    for po in r["parts"]:
        lines.append(f"### {po['name']}")
        lines.append(f"- Process: {po['process'] or 'TBD'} ({po['basis']}) · Material: {po['material'] or 'TBD'} · "
                     f"Confidence: {po['confidence']}")
        for risk in po["risks"]:
            lines.append(f"- Risk: {risk}")
        lines.append("")
    lines += ["## Open questions", ""]
    lines += [f"- **{q['part']}:** {q['question']}" for q in r["open_questions"]] or ["- None"]
    lines += ["", "## Assumptions", ""] + [f"- {a}" for a in r["assumptions"]]
    return "\n".join(lines) + "\n"
