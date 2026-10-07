"""Parameter-validation types shared by every CAD generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationIssue:
    param: str | None
    message: str
    level: str = "error"  # error | warning

    def as_dict(self) -> dict[str, Any]:
        return {"param": self.param, "message": self.message, "level": self.level}


@dataclass
class ValidationResult:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [e.as_dict() for e in self.errors],
            "warnings": [w.as_dict() for w in self.warnings],
        }


@dataclass(frozen=True)
class WallLimit:
    """Wall thickness limits from the rules data for the process chosen for a part."""

    process_name: str
    min: float
    max: float
    typical_min: float
    typical_max: float
    verified: bool = False
