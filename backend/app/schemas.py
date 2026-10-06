"""Pydantic schemas for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PowerType = Literal["mains", "battery", "passive", "undecided"]


class Dimensions(BaseModel):
    height_mm: float | None = None
    width_mm: float | None = None
    depth_mm: float | None = None


class Money(BaseModel):
    amount: float | None = None
    currency: str = "GBP"


class Requirements(BaseModel):
    """Product requirements. `None` means TBD."""

    approx_dimensions: Dimensions = Field(default_factory=Dimensions)
    target_retail_price: Money = Field(default_factory=Money)
    production_volume: int | None = Field(default=None, description="Expected units per year")
    target_unit_cost: Money = Field(default_factory=Money)
    intended_markets: list[str] = Field(default_factory=list)
    power_type: PowerType = "undecided"
    battery_runtime_h: float | None = Field(default=None, description="Target runtime at full brightness (hours)")
    preferred_materials: list[str] = Field(default_factory=list)
    preferred_finishes: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    environmental_requirements: list[str] = Field(default_factory=list)


REQUIREMENT_FIELDS = list(Requirements.model_fields)


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    template: Literal["faro"] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    requirements: Requirements | None = None
    assumed_fields: list[str] | None = None


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    path: str
    kind: str
    caption: str
    uploaded_at: datetime


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str
    template: str | None
    created_at: datetime
    updated_at: datetime


class ProjectOut(ProjectSummary):
    requirements: Requirements
    assumed_fields: list[str]
    images: list[ImageOut]


class PartBase(BaseModel):
    parent_id: int | None = None
    cad_key: str | None = None
    name: str
    function: str = ""
    quantity: int = Field(default=1, ge=1)
    material_category: str = "other"
    material: str = ""
    process: str = ""
    finish: str = ""
    traits: list[str] = Field(default_factory=list)
    dimensions: str = ""
    tolerances: str = ""
    supplier_notes: str = ""
    cost_low: float | None = Field(default=None, ge=0)
    cost_high: float | None = Field(default=None, ge=0)
    open_questions: list[str] = Field(default_factory=list)
    sort_order: int = 0


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    parent_id: int | None = None
    cad_key: str | None = None
    name: str | None = None
    function: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    material_category: str | None = None
    material: str | None = None
    process: str | None = None
    finish: str | None = None
    traits: list[str] | None = None
    dimensions: str | None = None
    tolerances: str | None = None
    supplier_notes: str | None = None
    cost_low: float | None = Field(default=None, ge=0)
    cost_high: float | None = Field(default=None, ge=0)
    open_questions: list[str] | None = None
    sort_order: int | None = None


class PartOut(PartBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int


class CadOutputOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    part_key: str | None
    format: str
    path: str


class CadModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version: int
    generator: str
    parameters: dict[str, Any]
    part_info: dict[str, Any]
    created_at: datetime
    outputs: list[CadOutputOut]


class DecisionIn(BaseModel):
    part_id: int | None = None
    topic: str = "material_process"
    status: Literal["accepted", "rejected", "edited", "proposed"]
    recommendation: dict[str, Any] = Field(default_factory=dict)
    chosen: dict[str, Any] = Field(default_factory=dict)
    note: str = ""


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    part_id: int | None
    topic: str
    status: str
    recommendation: dict[str, Any]
    chosen: dict[str, Any]
    note: str
    created_at: datetime
    updated_at: datetime


class RevisionCreate(BaseModel):
    note: str = ""


class RevisionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: int
    note: str
    created_at: datetime


class RevisionOut(RevisionSummary):
    snapshot: dict[str, Any]
