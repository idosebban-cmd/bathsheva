"""Product templates a project can be created from."""

from __future__ import annotations

from fastapi import APIRouter

from app.products import products

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
def list_templates() -> list[dict[str, str]]:
    return [{"key": p.key, "label": p.label, "summary": p.summary, "noun": p.noun} for p in products().values()]
