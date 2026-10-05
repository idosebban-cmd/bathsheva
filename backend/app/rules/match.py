"""Map free-text part fields (as typed or accepted by the user) to rule keys."""

from __future__ import annotations

from app.rules.data import RuleSet


def _norm(s: str) -> str:
    return " ".join(s.lower().replace("_", " ").replace("-", " ").split())


def match_process(rules: RuleSet, text: str) -> str | None:
    t = _norm(text)
    if not t:
        return None
    for key, proc in rules.processes.items():
        if t in (_norm(key), _norm(proc.name)):
            return key
    for key, proc in rules.processes.items():
        if _norm(proc.name) in t or _norm(key) in t:
            return key
    return None


def match_material(rules: RuleSet, text: str) -> str | None:
    t = _norm(text)
    if not t:
        return None
    for key, mat in rules.materials.items():
        if t in (_norm(key), _norm(mat.name)):
            return key
    for key, mat in rules.materials.items():
        if _norm(mat.name) in t:
            return key
    return None


def match_finishes(rules: RuleSet, text: str) -> list[str]:
    t = _norm(text)
    return [k for k, f in rules.finishes.items() if any(kw in t for kw in f.keywords)]
