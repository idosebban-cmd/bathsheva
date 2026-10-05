"""Loading and validating the rules seed data (backend/seed/rules/*.yaml).

Every entry must carry provenance: `source` and `confidence` are required,
`verified` defaults to False. Loading fails loudly if provenance is missing.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.config import SEED_DIR

Confidence = Literal["low", "medium", "high"]
FinishQuality = Literal["poor", "fair", "good", "excellent"]
FINISH_RANK = {"poor": 0, "fair": 1, "good": 2, "excellent": 3}
CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1)
    confidence: Confidence
    verified: bool = False


class Range(BaseModel):
    min: float
    max: float


class WallRange(BaseModel):
    min: float
    max: float
    typical_min: float
    typical_max: float


class Process(Provenance):
    key: str
    name: str
    material_categories: list[str]
    plain_language: str
    requires_all: list[str] = []
    excludes: list[str] = []
    suits: list[str] = []
    poor_fit: list[str] = []
    volume: Range
    tooling_cost: str
    unit_cost: Literal["low", "medium", "high"]
    finish_quality: FinishQuality
    wall_mm: WallRange | None
    when_to_prefer: str
    risks: list[str] = []


class Material(Provenance):
    key: str
    name: str
    category: str
    processes: list[str]
    plain_language: str
    finish_compat: dict[str, Literal["good", "fair", "poor"]] = {}
    max_service_temp_c: float | None = None
    density_g_cm3: float | None = None
    is_glass: bool = False


class Finish(Provenance):
    key: str
    name: str
    keywords: list[str]
    plain_language: str
    min_process_finish: FinishQuality
    notes: str = ""


class BendRadius(Provenance):
    material: str
    min_radius_t: float
    plain_language: str


class Tolerance(Provenance):
    process: str
    general_mm: float
    precision_mm: float
    plain_language: str


class DraftAngle(Provenance):
    process: str
    external_deg: float
    internal_deg: float
    plain_language: str


class Fastener(Provenance):
    key: str
    name: str
    plain_language: str
    notes: str = ""
    safety: bool = False


class ToolingCost(Provenance):
    key: str
    name: str
    gbp_min: float
    gbp_max: float


class SafetyRule(Provenance):
    key: str
    message: str
    verify_with: str
    traits_any: list[str] = []
    categories_any: list[str] = []
    materials_any: list[str] = []
    processes_any: list[str] = []
    power_any: list[str] = []
    polymer_near_heat: bool = False


class PlanningValue(Provenance):
    key: str
    value: Any
    unit: str = ""
    plain_language: str


class RuleSet(BaseModel):
    processes: dict[str, Process]
    materials: dict[str, Material]
    finishes: dict[str, Finish]
    bend_radius: dict[str, BendRadius]
    tolerances: dict[str, Tolerance]
    draft_angles: dict[str, DraftAngle]
    fasteners: dict[str, Fastener]
    tooling_cost: dict[str, ToolingCost]
    safety_rules: list[SafetyRule]
    planning: dict[str, PlanningValue]

    def plan(self, key: str) -> Any:
        return self.planning[key].value


# file -> (top-level key, model, index field or None for list)
_FILES: dict[str, tuple[str, type[Provenance], str | None]] = {
    "processes.yaml": ("processes", Process, "key"),
    "materials.yaml": ("materials", Material, "key"),
    "finishes.yaml": ("finishes", Finish, "key"),
    "sheet_bend_radius.yaml": ("bend_radius", BendRadius, "material"),
    "tolerances.yaml": ("tolerances", Tolerance, "process"),
    "draft_angles.yaml": ("draft_angles", DraftAngle, "process"),
    "fasteners.yaml": ("fasteners", Fastener, "key"),
    "tooling_cost.yaml": ("tooling_cost", ToolingCost, "key"),
    "safety.yaml": ("safety_rules", SafetyRule, None),
    "planning.yaml": ("planning", PlanningValue, "key"),
}


class RulesDataError(ValueError):
    pass


def load_rules_from(directory: Path) -> RuleSet:
    data: dict[str, Any] = {}
    for filename, (top, model, index) in _FILES.items():
        path = directory / filename
        with path.open() as f:
            raw = yaml.safe_load(f) or {}
        entries = raw.get(top)
        if not isinstance(entries, list):
            raise RulesDataError(f"{filename}: expected a list under '{top}'")
        parsed = []
        for i, entry in enumerate(entries):
            try:
                parsed.append(model.model_validate(entry))
            except Exception as e:  # pydantic ValidationError
                raise RulesDataError(f"{filename} entry {i}: {e}") from e
        if index is None:
            data[top] = parsed
        else:
            keyed = {getattr(e, index): e for e in parsed}
            if len(keyed) != len(parsed):
                raise RulesDataError(f"{filename}: duplicate '{index}' values")
            data[top] = keyed
    rules = RuleSet(**data)
    _check_references(rules)
    return rules


def _check_references(rules: RuleSet) -> None:
    for p in rules.processes.values():
        if p.tooling_cost not in rules.tooling_cost:
            raise RulesDataError(f"process {p.key}: unknown tooling_cost {p.tooling_cost}")
    for m in rules.materials.values():
        for pk in m.processes:
            if pk not in rules.processes:
                raise RulesDataError(f"material {m.key}: unknown process {pk}")
        for fk in m.finish_compat:
            if fk not in rules.finishes:
                raise RulesDataError(f"material {m.key}: unknown finish {fk}")
    for k in list(rules.tolerances) + list(rules.draft_angles):
        if k not in rules.processes:
            raise RulesDataError(f"unknown process {k} in tolerances/draft")
    for k in rules.bend_radius:
        if k not in rules.materials:
            raise RulesDataError(f"unknown material {k} in bend radius")


@lru_cache
def load_rules() -> RuleSet:
    return load_rules_from(SEED_DIR / "rules")


def source_ref(kind: str, key: str, entry: Provenance) -> dict[str, Any]:
    """A citation for a seed entry, shown in the UI."""
    return {
        "kind": kind,
        "key": key,
        "source": entry.source,
        "confidence": entry.confidence,
        "verified": entry.verified,
    }
