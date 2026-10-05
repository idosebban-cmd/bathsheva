"""ORM models.

Milestone 1 uses: Project, ReferenceImage, Part, CadModel, CadOutput,
EngineeringDecision, Revision.

Costing: CostItem holds editable bought-in / assembly / packaging lines; all
rates live in seed/cost/*.yaml.

Quotes: ExternalQuote records real supplier quotes / DFM feedback per part
for manual comparison. They never feed the rules engine automatically.

Schema-only (later milestones, no API yet): Supplier, FactoryFeedback,
FeedbackItem, KnowledgeEntry, ComplianceRecord.

Materials, processes and finishes are not tables: they live in the seed YAML
(`backend/seed/rules`) and are referenced by key (e.g. part.process_key).
"""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DecisionStatus(str, enum.Enum):
    proposed = "proposed"
    accepted = "accepted"
    rejected = "rejected"
    edited = "edited"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # Product template used to seed the project (e.g. "faro"); drives the CAD generator.
    template: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Structured requirements, validated by app.schemas.Requirements.
    requirements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Requirement field names whose values are placeholders / assumptions.
    assumed_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    images: Mapped[list[ReferenceImage]] = relationship(back_populates="project", cascade="all, delete-orphan")
    parts: Mapped[list[Part]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Part.sort_order"
    )
    cad_models: Mapped[list[CadModel]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="CadModel.version"
    )
    decisions: Mapped[list[EngineeringDecision]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    revisions: Mapped[list[Revision]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Revision.number"
    )


class ReferenceImage(Base):
    __tablename__ = "reference_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(300))
    # Path relative to the data directory.
    path: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(30), default="reference")  # concept | reference
    caption: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="images")


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("parts.id", ondelete="SET NULL"), nullable=True)
    # Key of the CAD body this part maps to (one body per part). None = not modelled.
    cad_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    function: Mapped[str] = mapped_column(Text, default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    # Material family used by the rules engine: aluminium | clear_polymer_or_glass | electrical | bought_in | other
    material_category: Mapped[str] = mapped_column(String(50), default="other")
    material: Mapped[str] = mapped_column(String(200), default="")
    process: Mapped[str] = mapped_column(String(200), default="")
    finish: Mapped[str] = mapped_column(String(200), default="")
    # Geometry traits for the rules engine (e.g. ["axisymmetric", "thin_wall"]).
    traits: Mapped[list[str]] = mapped_column(JSON, default=list)
    dimensions: Mapped[str] = mapped_column(Text, default="")
    tolerances: Mapped[str] = mapped_column(Text, default="")
    supplier_notes: Mapped[str] = mapped_column(Text, default="")
    cost_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    open_questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[Project] = relationship(back_populates="parts")


class CadModel(Base):
    """One generated version of a project's CAD. Immutable once generated."""

    __tablename__ = "cad_models"
    __table_args__ = (UniqueConstraint("project_id", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    generator: Mapped[str] = mapped_column(String(50))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON)
    # Per-part metadata from generation (bounding boxes, volumes).
    part_info: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="cad_models")
    outputs: Mapped[list[CadOutput]] = relationship(back_populates="cad_model", cascade="all, delete-orphan")


class CadOutput(Base):
    __tablename__ = "cad_outputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    cad_model_id: Mapped[int] = mapped_column(ForeignKey("cad_models.id", ondelete="CASCADE"))
    part_key: Mapped[str | None] = mapped_column(String(50), nullable=True)  # None = whole assembly
    format: Mapped[str] = mapped_column(String(10))  # step | stl | glb
    path: Mapped[str] = mapped_column(String(500))  # relative to data dir

    cad_model: Mapped[CadModel] = relationship(back_populates="outputs")


class EngineeringDecision(Base):
    """A user's response to a recommendation (or a project-level open decision)."""

    __tablename__ = "engineering_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    part_id: Mapped[int | None] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), nullable=True)
    topic: Mapped[str] = mapped_column(String(50))  # material_process | power_type | ...
    status: Mapped[DecisionStatus] = mapped_column(String(20), default=DecisionStatus.proposed)
    # The recommendation as generated at decision time.
    recommendation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # What the user chose (for accepted/edited).
    chosen: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped[Project] = relationship(back_populates="decisions")


class Revision(Base):
    """Immutable snapshot of a project's state. No branching or merging."""

    __tablename__ = "revisions"
    __table_args__ = (UniqueConstraint("project_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(Text, default="")
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="revisions")


class ExternalQuote(Base):
    """A real quote or DFM response from a supplier or quoting service (e.g. Xometry) for one part."""

    __tablename__ = "external_quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"))
    # Design revision the quote was made against (optional).
    revision_id: Mapped[int | None] = mapped_column(ForeignKey("revisions.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[str] = mapped_column(String(200))
    quote_date: Mapped[date] = mapped_column(Date)
    process: Mapped[str] = mapped_column(String(200), default="")
    material: Mapped[str] = mapped_column(String(200), default="")
    finish: Mapped[str] = mapped_column(String(200), default="")
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dfm_notes: Mapped[str] = mapped_column(Text, default="")
    # Uploaded quote document, relative to the data directory.
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attachment_filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CostItem(Base):
    """Editable product-level cost line: bought-in component, assembly labour or packaging."""

    __tablename__ = "cost_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))  # bought_in | assembly | packaging | other
    name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit: Mapped[str] = mapped_column(String(10), default="pcs")  # pcs | min
    # GBP per unit. Null for minute-based items: they use the seeded labour rate.
    unit_cost_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_cost_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_key: Mapped[str | None] = mapped_column(String(50), nullable=True)  # seed/cost/bought_in.yaml key
    source: Mapped[str] = mapped_column(String(300), default="model-generated")
    confidence: Mapped[str] = mapped_column(String(10), default="low")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# Schema-only entities for later milestones (factory feedback, knowledge base,
# compliance). No API or UI in Milestone 1.
# ---------------------------------------------------------------------------


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100), default="")
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)  # process keys
    contact: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FactoryFeedback(Base):
    __tablename__ = "factory_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    revision_id: Mapped[int | None] = mapped_column(ForeignKey("revisions.id", ondelete="SET NULL"), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FeedbackItem(Base):
    """A single requested change extracted from factory feedback."""

    __tablename__ = "feedback_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    feedback_id: Mapped[int] = mapped_column(ForeignKey("factory_feedback.id", ondelete="CASCADE"))
    part_id: Mapped[int | None] = mapped_column(ForeignKey("parts.id", ondelete="SET NULL"), nullable=True)
    requested_change: Mapped[str] = mapped_column(Text)
    likely_reason: Mapped[str] = mapped_column(Text, default="")
    proposed_revision: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[DecisionStatus] = mapped_column(String(20), default=DecisionStatus.proposed)


class KnowledgeEntry(Base):
    """Manufacturing knowledge base; reusable across products."""

    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    statement: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[str] = mapped_column(String(300), default="")
    confidence: Mapped[str] = mapped_column(String(10), default="low")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    area: Mapped[str] = mapped_column(String(100))  # electrical_safety | emc | rohs | weee | markings | ...
    # engineering_guidance | requirement_to_investigate | certified_signoff
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    detail: Mapped[str] = mapped_column(Text, default="")
    evidence_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # required for certified_signoff
    status: Mapped[str] = mapped_column(String(30), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
