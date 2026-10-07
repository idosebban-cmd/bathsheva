"""Product registry: one entry per product template (seed/products/<key>.yaml).

A product ties a template to its parametric CAD generator (`app.cad.<key>`, see
`app.cad.generator` for the interface) and to the few checks and data that only make
sense for that product (its DFM checks, which walls and drafts its parameters set,
typical densities of its bought-in bodies). Services ask the project's product for
these instead of naming a product, so adding one is a registry entry, a template and a
generator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from app.cad.validation import ValidationResult, WallLimit
    from app.models import Project
    from app.rules.data import RuleSet

# Check factory used by the DFM report: (area, level, title, detail, unverified=False, part=None) -> dict
CheckFn = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class Product:
    key: str  # template name, also Project.template
    label: str  # "Faro"
    summary: str  # what it is, for the "create project" button: "lighthouse lamp"
    noun: str  # one unit, in UI copy: "lamp"
    generator: ModuleType  # parametric CAD generator (app.cad.<key>)
    # Validate parameters against the rules data: (params, wall limits per cad_key, rules) -> result
    validate: Callable[[dict[str, Any], dict[str, "WallLimit"], "RuleSet"], "ValidationResult"]
    # Parts whose wall the CAD validation checks against the part's process: cad_key -> planning key of a
    # general fallback range used when the part has no process with wall limits (None = no fallback)
    wall_limit_parts: dict[str, str | None] = field(default_factory=dict)
    # Parameter holding the wall thickness of a part, for the DFM wall check: cad_key -> parameter
    wall_params: dict[str, str] = field(default_factory=dict)
    # DFM draft check per part: (cad_key, params) -> ("taper", degrees) | ("vertical", None) | None
    draft: Callable[[str, dict[str, Any]], tuple[str, float | None] | None] = lambda cad_key, params: None
    # Product-specific DFM checks (geometry, thermal, assembly, mass): (project, params, rules, check) -> checks
    dfm_checks: Callable[["Project", dict[str, Any], "RuleSet", CheckFn], list[dict[str, Any]]] | None = None
    # Typical densities for bought-in bodies in the mass estimate: cad_key -> (rules material key | None, g/cm³)
    bought_in_density: dict[str, tuple[str | None, float]] = field(default_factory=dict)
    # Whether the Factory Pack (RFQ, drawings, supplier BOM) is implemented for this product
    factory_pack: bool = False


def _registry() -> dict[str, Product]:
    from app.products import faro

    return {p.key: p for p in (faro.PRODUCT,)}


_PRODUCTS: dict[str, Product] | None = None


def products() -> dict[str, Product]:
    """Every registered product, by template key (in display order)."""
    global _PRODUCTS
    if _PRODUCTS is None:
        _PRODUCTS = _registry()
    return _PRODUCTS


def get_product(key: str | None) -> Product | None:
    return products().get(key or "")


def product_for(project: "Project") -> Product | None:
    """The project's product, or None for a project not created from a template."""
    return get_product(project.template)
