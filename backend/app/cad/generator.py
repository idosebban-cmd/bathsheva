"""The interface every parametric CAD generator module implements (app.cad.<product>).

A generator is a plain module, registered for its product in `app.products`. The
services and the API use only the names below, so a new product's generator must
define all of them; `tests/test_products.py` checks every registered generator.
"""

from __future__ import annotations

from typing import Any, Protocol

from build123d import Compound, Shape

from app.cad.validation import ValidationResult, WallLimit


class Generator(Protocol):
    GENERATOR: str  # stored on each CadModel version
    PARAMS: list[Any]  # ParamDef-like dataclasses: key, label, group, unit, min, max, ... (served to the CAD tab)
    PART_KEYS: list[str]  # body names; a template part's cad_key is one of these
    PART_COLOURS: dict[str, tuple[float, float, float, float]]  # RGBA per body (STEP and GLB colours)
    UNSCALED_PARAMS: set[str]  # parameters that don't scale with overall height (cost-down height scenarios)
    PRODUCTION_CHANGES: list[dict[str, str]]  # every departure from the approved prototype
    IMPLEMENTED_CHANGES: dict[str, set[str]]  # route design-change key -> bodies that show it in the CAD

    def validate(self, params: dict[str, Any], wall_limits: dict[str, WallLimit] | None = None,
                 *args: Any) -> ValidationResult: ...

    def normalise(self, params: dict[str, Any]) -> dict[str, float | int]: ...

    def upgrade(self, params: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]: ...

    def build(self, params: dict[str, Any]) -> dict[str, Shape]: ...  # one solid per body

    def assembly(self, parts: dict[str, Shape], name: str = ...) -> Compound: ...

    def preview_two_tone(self, params: dict[str, Any]) -> dict[str, dict[str, Any]]: ...

    def preview_extras(self, params: dict[str, Any]) -> dict[str, tuple[Shape, tuple]]: ...

    def public_derived(self, params: dict[str, Any]) -> dict[str, Any]: ...

    def derived_traits(self, part_key: str, params: dict[str, Any]) -> list[str]: ...

    def implements(self, change_key: str, cad_key: str | None, bodies: set[str]) -> bool: ...

    def production_change_checks(self, params: dict[str, Any]) -> list[dict[str, Any]]: ...

    def estimate_mass(self, part_info: dict[str, Any], densities: dict[str, float]) -> dict[str, Any]: ...


# Names a generator module must define (the Protocol above, as a checklist for tests).
REQUIRED = ("GENERATOR", "PARAMS", "PART_KEYS", "PART_COLOURS", "UNSCALED_PARAMS", "PRODUCTION_CHANGES",
            "IMPLEMENTED_CHANGES", "validate", "normalise", "upgrade", "build", "assembly", "preview_two_tone",
            "preview_extras", "public_derived", "derived_traits", "implements", "production_change_checks",
            "estimate_mass")
