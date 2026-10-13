"""Standard off-the-shelf parts library, the product concepts in standard-parts/, and saved concepts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app import standard_parts as sp
from app.db import get_session
from app.models import Concept
from app.services import concepts

router = APIRouter(tags=["standard-parts"])


class LineView(BaseModel):
    """Where the 3D view puts a line's part: offsets from its place in the stack (mm), rotation (degrees),
    copies spaced evenly round the vertical axis, whether it adds its height to the stack, and how a sheet
    part is drawn (as cut: a flat sheet, a disc, or rolled into a tube), or the shape the line is made into."""

    dx: float = Field(default=0, ge=-5000, le=5000)
    dy: float = Field(default=0, ge=-5000, le=5000)
    dz: float = Field(default=0, ge=-5000, le=5000)
    rx: float = Field(default=0, ge=-360, le=360)
    ry: float = Field(default=0, ge=-360, le=360)
    rz: float = Field(default=0, ge=-360, le=360)
    repeat: int = Field(default=1, ge=1, le=64)
    stack: bool = True
    form: Literal["auto", "sheet", "disc", "rolled"] = "auto"
    made: dict[str, Any] | None = None  # drawn as the part the line is made into (a turned plinth), not its stock

    @field_validator("made")
    @classmethod
    def _made(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return None
        try:
            return sp.made_shape(v)
        except sp.LibraryError as e:
            raise ValueError(str(e)) from e


class LineIn(BaseModel):
    part_id: str
    # In the part's priced unit; ignored when sizes in mm are given for a part priced by length or area.
    quantity: float = Field(default=0, ge=0)
    note: str = ""
    option: int = Field(default=0, ge=0)
    length_mm: float | None = Field(default=None, ge=0)
    width_mm: float | None = Field(default=None, ge=0)
    height_mm: float | None = Field(default=None, ge=0)
    count: float | None = Field(default=None, ge=0)
    waste_pct: float | None = Field(default=None, ge=0, le=500)
    view: LineView | None = None  # 3D view only; doesn't affect cost


class CostIn(BaseModel):
    lines: list[LineIn] = []
    retail_price: float | None = Field(default=None, gt=0)


class ConceptIn(CostIn):
    name: str = Field(min_length=1, max_length=200)
    based_on: str | None = None
    notes: str = ""


class ConceptOut(BaseModel):
    id: int
    name: str
    retail_price: float | None
    based_on: str | None
    lines: list[dict[str, Any]]
    notes: str
    created_at: datetime
    updated_at: datetime
    cost: dict[str, Any]

    @field_validator("created_at", "updated_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        # SQLite drops the zone; the timestamps are UTC (as schemas.ProjectSummary).
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)


@router.get("/api/standard-parts")
def library() -> dict[str, Any]:
    return concepts.library_payload()


@router.get("/api/standard-parts/concepts")
def seed_concepts() -> list[dict[str, Any]]:
    return concepts.seed_concepts()


@router.post("/api/standard-parts/cost")
def cost(body: CostIn) -> dict[str, Any]:
    return concepts.cost([ln.model_dump() for ln in body.lines], body.retail_price)


@router.get("/api/concepts", response_model=list[ConceptOut])
def list_concepts(session: Session = Depends(get_session)):
    return concepts.list_concepts(session)


def _get(concept_id: int, session: Session) -> Concept:
    row = session.get(Concept, concept_id)
    if row is None:
        raise HTTPException(404, "Concept not found")
    return row


def _save(body: ConceptIn, session: Session, row: Concept | None = None) -> dict[str, Any]:
    try:
        row = concepts.save_concept(session, body.model_dump(), row)
    except concepts.UnknownParts as e:
        raise HTTPException(422, str(e)) from e
    return concepts.concept_out(row)


@router.post("/api/concepts", response_model=ConceptOut, status_code=201)
def create_concept(body: ConceptIn, session: Session = Depends(get_session)):
    return _save(body, session)


@router.get("/api/concepts/{concept_id}", response_model=ConceptOut)
def get_concept(concept_id: int, session: Session = Depends(get_session)):
    return concepts.concept_out(_get(concept_id, session))


@router.put("/api/concepts/{concept_id}", response_model=ConceptOut)
def update_concept(concept_id: int, body: ConceptIn, session: Session = Depends(get_session)):
    return _save(body, session, _get(concept_id, session))


@router.delete("/api/concepts/{concept_id}", status_code=204)
def delete_concept(concept_id: int, session: Session = Depends(get_session)):
    session.delete(_get(concept_id, session))
    session.commit()
