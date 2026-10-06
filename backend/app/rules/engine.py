"""Deterministic rules engine: material/process recommendations per part.

Pure functions: inputs are plain dicts, output is a JSON-serialisable dict.
No database or LLM access here. The LLM may later *explain* a recommendation
but never changes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.rules.data import CONFIDENCE_RANK, FINISH_RANK, DesignConstraint, Material, Process, RuleSet, source_ref
from app.rules.match import match_finishes

# Plain-language phrases for geometry traits.
TRAIT_TEXT = {
    "axisymmetric": "round (symmetrical about its axis)",
    "thin_wall": "thin-walled",
    "open_both_ends": "an open-ended tube",
    "closed_top": "closed at one end",
    "domed": "domed",
    "tapered": "tapered",
    "constant_section": "the same cross-section along its length",
    "ring": "a ring",
    "short": "short",
    "mounting_holes": "has mounting holes",
    "side_hole": "has a side hole",
    "needs_mass": "needs weight for stability",
    "cosmetic": "a visible, cosmetic part",
    "transparent": "transparent",
    "near_heat_source": "close to the LED",
    "electrical": "electrical",
    "heat_source": "produces heat",
    "internal": "hidden inside the product",
    "strain_relief": "needs cable strain relief",
    "user_accessible": "handled by the user",
    "non_axisymmetric": "not round",
    "hidden": "hidden inside the product",
    "visible_trim": "has a visible metal element (e.g. a knob)",
}

# Which CAD parameter holds the wall thickness for a part.
WALL_PARAM = {
    "base": "wall_thickness",
    "main_body": "wall_thickness",
    "band": "wall_thickness",
    "top_cap": "wall_thickness",
    "lantern": "lantern_wall_thickness",
}

COMPAT_SCORE = {"good": 2, "fair": 0.5, "poor": -2}
# Volumes used for the "would the answer change?" sensitivity check.
SENSITIVITY_VOLUMES = [100, 1000, 10000]


@dataclass
class Context:
    """Project-level inputs to the rules engine."""

    power_type: str = "undecided"
    production_volume: int | None = None
    cad_parameters: dict[str, Any] = field(default_factory=dict)
    joints: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _Scored:
    process: Process
    material: Material | None
    score: float
    reasons: list[str]
    concerns: list[str]


def _fmt_volume(n: float) -> str:
    return f"{int(n):,}"


def _tooling_text(rules: RuleSet, key: str) -> str:
    t = rules.tooling_cost[key]
    if t.gbp_max == 0:
        return "no tooling cost"
    return f"{t.name.lower()} tooling cost (roughly £{_fmt_volume(t.gbp_min)}–£{_fmt_volume(t.gbp_max)})"


def _best_material(rules: RuleSet, process: Process, finish_keys: list[str],
                   kinds: set[str] | None = None) -> tuple[Material | None, float, list[str]]:
    """Pick the material most commonly paired with the process that suits the finishes.

    `kinds` restricts the choice to material kinds a design constraint allows (None = any).
    """
    best: tuple[Material | None, float, list[str]] = (None, float("-inf"), [])
    for mat in rules.materials.values():
        if process.key not in mat.processes:
            continue
        if kinds is not None and mat.material_kind not in kinds:
            continue
        preference = -0.3 * mat.processes.index(process.key)
        compat = 0.0
        notes: list[str] = []
        for fk in finish_keys:
            level = mat.finish_compat.get(fk)
            if level is None:
                continue
            compat += COMPAT_SCORE[level]
            if level == "poor":
                notes.append(f"{mat.name} takes {rules.finishes[fk].name.lower()} poorly")
        score = preference + compat
        if score > best[1]:
            best = (mat, score, notes)
    return best


def active_constraints(rules: RuleSet, traits: set[str], category: str) -> list[DesignConstraint]:
    """Design constraints that apply to a part with these traits and material category."""
    return [c for c in rules.design_constraints.values() if c.applies(traits, category)]


def allowed_kinds(rules: RuleSet, traits: set[str], category: str) -> tuple[set[str] | None, DesignConstraint | None]:
    """Material kinds the part may use under the active constraints (None = unrestricted)."""
    kinds: set[str] | None = None
    first: DesignConstraint | None = None
    for c in active_constraints(rules, traits, category):
        k = c.kinds_for(traits)
        kinds = k if kinds is None else kinds & k
        first = first or c
    return kinds, first


def material_allowed(rules: RuleSet, traits: set[str], category: str, material_key: str | None,
                     finish_key: str | None = None) -> tuple[bool, str]:
    """Whether a material (and finish) is allowed on a part under the design constraints."""
    kinds, constraint = allowed_kinds(rules, traits, category)
    if constraint is None:
        return True, ""
    mat = rules.materials.get(material_key or "")
    kind = mat.material_kind if mat else ("metal" if material_key == "brass" else None)
    if kind is not None and kind not in kinds:
        return False, f"{constraint.name}: {mat.name if mat else material_key} is {kind}"
    fin = rules.finishes.get(finish_key or "")
    if fin is not None and fin.metal_effect:
        return False, f"{constraint.name}: {fin.name.split(' (')[0].lower()} imitates metal"
    return True, ""


def _score(
    rules: RuleSet, process: Process, traits: set[str], volume: float, finish_keys: list[str], wall: float | None,
    category: str = "",
) -> _Scored | tuple[str, str | None]:
    """Score one candidate process, or return a plain-language exclusion reason (and constraint key, if any)."""
    missing = [t for t in process.requires_all if t not in traits]
    if missing:
        return f"only works for parts that are {', '.join(TRAIT_TEXT.get(t, t) for t in missing)}", None
    blocked = [t for t in process.excludes if t in traits]
    if blocked:
        return f"not suited to parts that are {', '.join(TRAIT_TEXT.get(t, t) for t in blocked)}", None

    score = 0.0
    reasons: list[str] = []
    concerns: list[str] = []

    good = [t for t in process.suits if t in traits]
    if good:
        score += len(good)
        reasons.append(f"Suits parts that are {', '.join(TRAIT_TEXT.get(t, t) for t in good)}.")
    bad = [t for t in process.poor_fit if t in traits]
    if bad:
        score -= len(bad)
        concerns.append(f"Less suited to parts that are {', '.join(TRAIT_TEXT.get(t, t) for t in bad)}.")

    vmin, vmax = process.volume.min, process.volume.max
    if vmin <= volume <= vmax:
        score += 2
        reasons.append(f"Economic at {_fmt_volume(volume)} units (typical range {_fmt_volume(vmin)}–{_fmt_volume(vmax)}).")
    elif volume < vmin:
        score -= 2 + (1 if process.tooling_cost in ("high", "very_high") else 0)
        concerns.append(f"Usually uneconomic below about {_fmt_volume(vmin)} units because of tooling cost.")
    else:
        score -= 1.5
        concerns.append(f"Becomes relatively expensive above about {_fmt_volume(vmax)} units.")

    if process.tooling_cost in ("none", "low"):
        score += 0.5
        reasons.append(f"{_tooling_text(rules, process.tooling_cost).capitalize()}.")

    if "cosmetic" in traits:
        need = rules.plan("cosmetic_min_finish_quality")
        if FINISH_RANK[process.finish_quality] < FINISH_RANK[need]:
            score -= 1.5
            concerns.append(f"As-made surface is {process.finish_quality}; a visible part will need extra finishing work.")
        elif FINISH_RANK[process.finish_quality] >= FINISH_RANK["good"]:
            reasons.append(f"Gives a {process.finish_quality} surface for a visible part.")
    for fk in finish_keys:
        need = rules.finishes[fk].min_process_finish
        if FINISH_RANK[process.finish_quality] < FINISH_RANK[need]:
            score -= 0.5
            concerns.append(f"Needs surface preparation before {rules.finishes[fk].name.lower()}.")

    if wall is not None and process.wall_mm is not None:
        w = process.wall_mm
        if not w.min <= wall <= w.max:
            return f"cannot make the current {wall:g} mm wall (possible range {w.min:g}–{w.max:g} mm)", None
        if w.typical_min <= wall <= w.typical_max:
            score += 0.5
        else:
            concerns.append(f"Current wall thickness {wall:g} mm is outside the typical {w.typical_min:g}–{w.typical_max:g} mm.")

    kinds, constraint = allowed_kinds(rules, traits, category)
    material, mat_score, mat_notes = _best_material(rules, process, finish_keys, kinds)
    if material is None:
        if constraint is not None and _best_material(rules, process, finish_keys)[0] is not None:
            names = ", ".join(sorted({m.name for m in rules.materials.values() if process.key in m.processes}))
            return (f"excluded by the design constraint \"{constraint.name}\": it only works with {names}",
                    constraint.key)
        return "no material in the rules data is paired with this process", None
    if mat_score < 0:
        score -= 1
    concerns.extend(n + "." for n in mat_notes)
    return _Scored(process, material, score, reasons, concerns)


def _rank(rules: RuleSet, part: dict[str, Any], traits: set[str], volume: float, finish_keys: list[str], wall: float | None):
    scored: list[_Scored] = []
    excluded: list[dict[str, str]] = []
    for proc in rules.processes.values():
        if part["material_category"] not in proc.material_categories:
            continue
        result = _score(rules, proc, traits, volume, finish_keys, wall, part["material_category"])
        if isinstance(result, tuple):
            reason, constraint_key = result
            excluded.append({"process_key": proc.key, "process_name": proc.name, "reason": reason,
                             "constraint": constraint_key})
        else:
            scored.append(result)
    # Highest score first; cheaper tooling breaks ties.
    tooling_order = list(rules.tooling_cost)
    scored.sort(key=lambda s: (-s.score, tooling_order.index(s.process.tooling_cost)))
    return scored, excluded


def _safety_flags(rules: RuleSet, traits: set[str], category: str, material: Material | None,
                  process: Process | None, power: str) -> list[dict[str, Any]]:
    flags = []
    for rule in rules.safety_rules:
        if rule.traits_any and not traits & set(rule.traits_any):
            continue
        if rule.categories_any and category not in rule.categories_any:
            continue
        if rule.materials_any and (material is None or material.key not in rule.materials_any):
            continue
        if rule.processes_any and (process is None or process.key not in rule.processes_any):
            continue
        if rule.power_any and power not in rule.power_any:
            continue
        if rule.polymer_near_heat:
            is_polymer = material is not None and material.category == "clear_polymer_or_glass" and not material.is_glass
            if not (is_polymer and "near_heat_source" in traits):
                continue
        flags.append({
            "key": rule.key,
            "message": " ".join(rule.message.split()),
            "verify_with": rule.verify_with,
            "verified": rule.verified,
        })
    return flags


def recommend(rules: RuleSet, part: dict[str, Any], ctx: Context) -> dict[str, Any]:
    """Recommend a material/process combination for one part."""
    cad_key = part.get("cad_key")
    traits = set(part.get("traits") or [])
    derived = set(part.get("derived_traits") or [])
    traits |= derived
    category = part.get("material_category") or "other"
    finish_keys = match_finishes(rules, part.get("finish") or "")
    power = ctx.power_type or "undecided"

    volume_known = ctx.production_volume is not None
    volume = float(ctx.production_volume) if volume_known else float(rules.plan("assumed_volume_when_unknown"))

    wall_param = WALL_PARAM.get(cad_key or "")
    wall = None
    if wall_param and ctx.cad_parameters.get(wall_param) is not None:
        wall = float(ctx.cad_parameters[wall_param])

    sources: list[dict[str, Any]] = []
    assumptions: list[str] = []
    questions: list[str] = [q for q in (part.get("open_questions") or []) if q.strip()]

    if not volume_known:
        assumptions.append(
            f"Production volume is not set, so this assumes about {_fmt_volume(volume)} units (placeholder)."
        )
        sources.append(source_ref("planning", "assumed_volume_when_unknown", rules.planning["assumed_volume_when_unknown"]))
    if derived:
        assumptions.append(
            "Shape treated as " + ", ".join(TRAIT_TEXT.get(t, t) for t in sorted(derived)) + " (from current CAD parameters)."
        )
    if wall is not None:
        assumptions.append(f"Wall thickness {wall:g} mm (from current CAD parameters).")
    if part.get("finish"):
        assumptions.append(f"Target finish: {part['finish']}.")

    scored, excluded = _rank(rules, part, traits, volume, finish_keys, wall)

    # Design constraints: which apply, which processes they exclude, and any finish that breaks them.
    constraints = []
    for c in rules.design_constraints.values():
        applies = c.applies(traits, category)
        trim = bool(traits & set(c.trim_traits))
        if not (applies or trim):
            continue
        violations = [f"{rules.finishes[fk].name.split(' (')[0]} imitates metal and is not allowed on a visible part."
                      for fk in finish_keys if rules.finishes[fk].metal_effect] if applies else []
        constraints.append({
            "key": c.key, "name": c.name, "message": " ".join(c.message.split()),
            "scope": "part" if applies else "visible_trim",
            "requirement": ("Visible parts of this bought-in component (e.g. the knob) must be solid metal."
                            if trim and not applies else ""),
            "excluded_processes": [e["process_name"] for e in excluded if e.get("constraint") == c.key],
            "violations": violations, "source": c.source,
        })

    base = {
        "part_id": part.get("id"),
        "part_key": cad_key,
        "part_name": part.get("name"),
        "inputs": {
            "traits": sorted(traits),
            "material_category": category,
            "volume": volume,
            "volume_assumed": not volume_known,
            "finish_keys": finish_keys,
            "wall_thickness_mm": wall,
            "power_type": power,
        },
    }

    if not scored:
        return {
            **base,
            "status": "no_match",
            "summary": "No process in the rules data fits this part. Add rules or set material and process manually.",
            "reason": [],
            "recommendation": None,
            "assumptions": assumptions,
            "confidence": "low",
            "confidence_reason": "No matching rule data.",
            "alternatives": [],
            "viable": [],
            "excluded": excluded,
            "constraints": constraints,
            "open_questions": questions or ["What is this part made from, and how?"],
            "risks": [],
            "technical": {},
            "safety_flags": _safety_flags(rules, traits, category, None, None, power),
            "sources": sources,
            "uses_unverified_data": any(not s["verified"] for s in sources),
        }

    top = scored[0]
    proc, mat = top.process, top.material
    assert mat is not None
    sources.append(source_ref("process", proc.key, proc))
    sources.append(source_ref("material", mat.key, mat))
    for fk in finish_keys:
        sources.append(source_ref("finish", fk, rules.finishes[fk]))
    sources.append(source_ref("tooling_cost", proc.tooling_cost, rules.tooling_cost[proc.tooling_cost]))

    # Technical detail.
    technical: dict[str, Any] = {
        "economic_volume": f"{_fmt_volume(proc.volume.min)}–{_fmt_volume(proc.volume.max)} units",
        "tooling_cost": _tooling_text(rules, proc.tooling_cost),
        "unit_cost": proc.unit_cost,
        "as_made_finish": proc.finish_quality,
    }
    if proc.wall_mm:
        w = proc.wall_mm
        technical["wall_thickness"] = (
            f"{w.typical_min:g}–{w.typical_max:g} mm typical (possible {w.min:g}–{w.max:g} mm)"
            + (f"; currently {wall:g} mm" if wall is not None else "")
        )
    tol = rules.tolerances.get(proc.key)
    if tol:
        technical["tolerances"] = tol.plain_language
        sources.append(source_ref("tolerance", proc.key, tol))
    draft = rules.draft_angles.get(proc.key)
    if draft:
        technical["draft_angles"] = f"{draft.plain_language} (external {draft.external_deg:g}°, internal {draft.internal_deg:g}°)"
        sources.append(source_ref("draft_angle", proc.key, draft))
    bend = rules.bend_radius.get(mat.key)
    if bend and proc.key == "sheet_forming":
        t = wall or 1.0
        technical["bend_radius"] = f"Minimum inside bend radius ≈ {bend.min_radius_t:g} × t = {bend.min_radius_t * t:.1f} mm. {bend.plain_language}"
        sources.append(source_ref("bend_radius", mat.key, bend))
    fastening = []
    for joint in ctx.joints:
        if cad_key and cad_key in joint.get("between", []):
            fast = rules.fasteners.get(joint["method"])
            if fast is None:
                continue
            other = [k for k in joint["between"] if k != cad_key][0]
            fastening.append(f"To {other.replace('_', ' ')}: {fast.name}. {joint.get('note', '')} {fast.notes}".strip())
            sources.append(source_ref("fastener", fast.key, fast))
    if fastening:
        technical["fastening"] = fastening
    finishing = []
    for fk in finish_keys:
        fin = rules.finishes[fk]
        compat = mat.finish_compat.get(fk)
        text = f"{fin.name}: {fin.plain_language.strip()}"
        if compat:
            text += f" Compatibility with {mat.name}: {compat}."
        if fin.notes:
            text += f" {fin.notes}"
        finishing.append(text)
    if finishing:
        technical["finishing"] = finishing

    # Alternatives.
    alternatives = []
    for alt in scored[1:4]:
        why_not = alt.concerns[:2] or [f"Scored lower than {proc.name.lower()} for this part."]
        alternatives.append({
            "process_key": alt.process.key,
            "process_name": alt.process.name,
            "material_key": alt.material.key if alt.material else None,
            "material_name": alt.material.name if alt.material else None,
            "when_to_prefer": alt.process.when_to_prefer,
            "why_not_chosen": why_not,
            "tooling_cost": _tooling_text(rules, alt.process.tooling_cost),
            "score": round(alt.score, 2),
        })

    # Sensitivity: does the answer change at other volumes?
    sensitivity = []
    for v in SENSITIVITY_VOLUMES:
        s, _ = _rank(rules, part, traits, float(v), finish_keys, wall)
        if s:
            sensitivity.append({"volume": v, "process_key": s[0].process.key, "process_name": s[0].process.name})
    volume_sensitive = len({s["process_key"] for s in sensitivity} | {proc.key}) > 1
    if not volume_known and not volume_sensitive:
        # The assumed volume did not influence the outcome; say so instead of leaning on it.
        sources = [s for s in sources if s["key"] != "assumed_volume_when_unknown"]
        assumptions[0] = (
            f"Production volume is not set; the recommendation is the same from {_fmt_volume(SENSITIVITY_VOLUMES[0])} "
            f"to {_fmt_volume(SENSITIVITY_VOLUMES[-1])} units."
        )

    # Confidence.
    margin = top.score - scored[1].score if len(scored) > 1 else 3.0
    level = "high" if margin >= 2 else "medium" if margin >= 1 else "low"
    why = [f"score margin over the next option is {margin:.1f}"]
    if not volume_known and volume_sensitive:
        level = "low"
        why.append("the best choice depends on production volume, which is not set")
    elif not volume_known:
        why.append("the choice does not depend on volume")
    data_conf = min((CONFIDENCE_RANK[s["confidence"]] for s in sources), default=2)
    if data_conf < CONFIDENCE_RANK[level]:
        level = ["low", "medium", "high"][data_conf]
        why.append("some rule data has low confidence")
    if any(not s["verified"] for s in sources) and level == "high":
        level = "medium"
        why.append("rule data is unverified")

    # Questions.
    if not volume_known and volume_sensitive:
        changes = ", ".join(f"{_fmt_volume(s['volume'])} units → {s['process_name'].lower()}" for s in sensitivity)
        questions.append(f"What production volume do you expect? The best process changes with volume ({changes}).")
    if power == "undecided" and (category in ("electrical", "aluminium")):
        questions.append("Mains or rechargeable battery? This changes the electrical design and safety requirements.")
    if "brass_plating" in finish_keys:
        questions.append("Brass details: solid brass, or real brass plating on the metal part? (Brass-look coatings are not allowed.)")

    safety = _safety_flags(rules, traits, category, mat, proc, power)
    for rule in rules.safety_rules:
        if any(f["key"] == rule.key for f in safety):
            sources.append(source_ref("safety_rule", rule.key, rule))

    if proc.key == "bought_in":
        summary = (
            f"Buy the {part.get('name', 'part').lower()} as a certified standard component rather than making it. "
            f"{proc.plain_language.strip()}"
        )
    else:
        summary = (
            f"Use {mat.name} made by {proc.name.lower()} for the {part.get('name', 'part').lower()}. "
            f"{mat.plain_language.strip()} {proc.when_to_prefer}"
        )
        if alternatives:
            a = alternatives[0]
            pref = a["when_to_prefer"].rstrip(".")
            summary += f" Main alternative: {a['process_name'].lower()} ({pref[0].lower()}{pref[1:]})."

    reason = [proc.plain_language.strip()] + top.reasons
    risks = list(proc.risks) + top.concerns

    deduped_sources = list({(s["kind"], s["key"]): s for s in sources}.values())
    return {
        **base,
        "status": "ok",
        "recommendation": {
            "process_key": proc.key,
            "process_name": proc.name,
            "material_key": mat.key,
            "material_name": mat.name,
            "finish": part.get("finish") or "",
        },
        "summary": " ".join(summary.split()),
        "reason": reason,
        "assumptions": assumptions,
        "confidence": level,
        "confidence_reason": "; ".join(why).capitalize() + ".",
        "alternatives": alternatives,
        # Every process that passed the hard exclusions, best first (for route costing).
        "viable": [
            {"process_key": v.process.key, "process_name": v.process.name, "material_key": v.material.key,
             "material_name": v.material.name, "score": round(v.score, 2)}
            for v in scored if v.material is not None
        ],
        "excluded": excluded,
        "constraints": constraints,
        "volume_sensitivity": sensitivity,
        "open_questions": list(dict.fromkeys(questions)),
        "risks": risks,
        "technical": technical,
        "safety_flags": safety,
        "sources": deduped_sources,
        "uses_unverified_data": any(not s["verified"] for s in deduped_sources),
    }
