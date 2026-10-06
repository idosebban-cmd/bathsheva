"""Cost model report and editable cost line items (Manufacturing tab)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.db import get_session
from app.models import CostItem, Project
from app.services.costing import cost_report, cost_settings, reset_items, update_cost_settings

PriceBasis = Literal["trade_volume", "distributor_small_qty", "retail", "model_estimate"]

router = APIRouter(prefix="/api/projects/{project_id}", tags=["costing"])


class CostItemIn(BaseModel):
    kind: Literal["bought_in", "assembly", "packaging", "finishing", "one_off", "other"] = "bought_in"
    name: str = Field(min_length=1)
    quantity: float = Field(default=1.0, gt=0)
    unit: Literal["pcs", "min"] = "pcs"
    unit_cost_low: float | None = Field(default=None, ge=0)
    unit_cost_high: float | None = Field(default=None, ge=0)
    source: str = "user"
    confidence: Literal["low", "medium", "high"] = "medium"
    verified: bool = False
    notes: str = ""
    price_basis: PriceBasis = "trade_volume"
    basis_quantity: float | None = Field(default=None, gt=0)
    discount_class: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "CostItemIn":
        if self.unit == "pcs" and self.unit_cost_low is None and self.unit_cost_high is None:
            raise ValueError("Give a unit cost (low and/or high) for a per-piece item")
        if self.unit_cost_low is not None and self.unit_cost_high is not None and self.unit_cost_high < self.unit_cost_low:
            raise ValueError("High cost must not be below low cost")
        return self


class CostItemUpdate(BaseModel):
    kind: Literal["bought_in", "assembly", "packaging", "other"] | None = None
    name: str | None = Field(default=None, min_length=1)
    quantity: float | None = Field(default=None, gt=0)
    unit_cost_low: float | None = Field(default=None, ge=0)
    unit_cost_high: float | None = Field(default=None, ge=0)
    source: str | None = None
    confidence: Literal["low", "medium", "high"] | None = None
    verified: bool | None = None
    notes: str | None = None
    price_basis: PriceBasis | None = None
    basis_quantity: float | None = Field(default=None, gt=0)
    discount_class: str | None = None


class CostItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    name: str
    quantity: float
    unit: str
    unit_cost_low: float | None
    unit_cost_high: float | None
    price_key: str | None
    source: str
    confidence: str
    verified: bool
    notes: str
    sort_order: int
    price_basis: str
    basis_quantity: float | None
    discount_class: str | None


class VolumeDiscountIn(BaseModel):
    low: float
    high: float


class CostSettingsIn(BaseModel):
    volume_discounts: dict[str, VolumeDiscountIn | None]


@router.get("/costs")
def get_costs(project: Project = Depends(get_project), session: Session = Depends(get_session)):
    return cost_report(session, project)


@router.get("/cost-items", response_model=list[CostItemOut])
def list_items(project: Project = Depends(get_project), session: Session = Depends(get_session)):
    return session.query(CostItem).filter(CostItem.project_id == project.id).order_by(CostItem.sort_order, CostItem.id).all()


@router.post("/cost-items", response_model=CostItemOut, status_code=201)
def add_item(body: CostItemIn, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    last = session.query(CostItem).filter(CostItem.project_id == project.id).order_by(CostItem.sort_order.desc()).first()
    item = CostItem(project_id=project.id, sort_order=(last.sort_order + 1) if last else 0, **body.model_dump())
    session.add(item)
    session.commit()
    return item


def _item(project: Project, item_id: int, session: Session) -> CostItem:
    item = session.get(CostItem, item_id)
    if item is None or item.project_id != project.id:
        raise HTTPException(404, "Cost item not found")
    return item


@router.patch("/cost-items/{item_id}", response_model=CostItemOut)
def update_item(item_id: int, body: CostItemUpdate, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    item = _item(project, item_id, session)
    changes = body.model_dump(exclude_unset=True)
    price_changed = any(k in changes for k in ("unit_cost_low", "unit_cost_high", "quantity"))
    for k, v in changes.items():
        setattr(item, k, v)
    if item.unit_cost_low is not None and item.unit_cost_high is not None and item.unit_cost_high < item.unit_cost_low:
        raise HTTPException(422, "High cost must not be below low cost")
    if item.unit == "pcs" and item.unit_cost_low is None and item.unit_cost_high is None:
        raise HTTPException(422, "A per-piece item needs a unit cost")
    # Editing a seeded price makes it the user's figure unless they say otherwise. A figure the
    # user types in is taken to be a volume price (e.g. a supplier quote), so no volume discount.
    if price_changed and "source" not in changes and item.source != "user":
        item.source = "user"
        if "price_basis" not in changes:
            item.price_basis, item.basis_quantity, item.discount_class = "trade_volume", None, None
    if item.discount_class:
        from app.costing.data import load_cost_data

        if item.discount_class not in load_cost_data().discount_classes():
            raise HTTPException(422, f"Unknown discount class {item.discount_class!r}")
    session.commit()
    return item


@router.delete("/cost-items/{item_id}", status_code=204)
def delete_item(item_id: int, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    session.delete(_item(project, item_id, session))
    session.commit()


@router.post("/cost-items/reset", response_model=list[CostItemOut])
def reset(project: Project = Depends(get_project), session: Session = Depends(get_session)):
    """Replace all cost items with the template defaults for the current power type."""
    if not project.template:
        raise HTTPException(409, "Only template projects have default cost items")
    return reset_items(session, project)


@router.get("/cost-settings")
def get_cost_settings(project: Project = Depends(get_project)):
    return cost_settings(project)


@router.put("/cost-settings")
def put_cost_settings(body: CostSettingsIn, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    return update_cost_settings(session, project, {k: (v.model_dump() if v else None) for k, v in body.volume_discounts.items()})


@router.get("/cost-audit")
def get_cost_audit(quantity: int = Query(500, ge=1, le=1_000_000), project: Project = Depends(get_project),
                   session: Session = Depends(get_session)):
    from app.services.cost_audit import cost_audit

    return cost_audit(session, project, quantity)


@router.get("/cost-audit.md")
def get_cost_audit_md(quantity: int = Query(500, ge=1, le=1_000_000), project: Project = Depends(get_project),
                      session: Session = Depends(get_session)):
    from fastapi.responses import Response

    from app.services.cost_audit import audit_markdown, cost_audit

    return Response(audit_markdown(cost_audit(session, project, quantity)), media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="{project.slug}-cost-assumptions-audit.md"'})


@router.get("/cost-audit.csv")
def get_cost_audit_csv(quantity: int = Query(500, ge=1, le=1_000_000), project: Project = Depends(get_project),
                       session: Session = Depends(get_session)):
    from fastapi.responses import Response

    from app.services.cost_audit import audit_csv, cost_audit

    return Response(audit_csv(cost_audit(session, project, quantity)), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{project.slug}-cost-assumptions-audit.csv"'})
