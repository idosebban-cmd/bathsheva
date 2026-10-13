"""Standard off-the-shelf parts library, the product concepts in standard-parts/, and saved concepts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Concept
from app.services import concepts

router = APIRouter(tags=["standard-parts"])


class LineIn(BaseModel):
    part_id: str
    quantity: float = Field(ge=0)
    note: str = ""
    option: int = Field(default=0, ge=0)


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
