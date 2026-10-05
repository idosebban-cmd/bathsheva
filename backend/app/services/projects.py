"""Project creation and helpers."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Part, Project
from app.schemas import Requirements
from app.services.templates import load_template


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


def unique_slug(session: Session, name: str) -> str:
    base = _slugify(name)
    slug, n = base, 2
    while session.scalar(select(Project.id).where(Project.slug == slug)) is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug


def create_project(session: Session, name: str, description: str = "", template: str | None = None) -> Project:
    requirements = Requirements()
    assumed: list[str] = []
    parts: list[Part] = []

    if template:
        tpl = load_template(template)
        description = description or tpl["description"].strip()
        requirements = Requirements.model_validate(tpl["requirements"])
        assumed = list(tpl.get("assumed_fields", []))
        for i, p in enumerate(tpl["parts"]):
            parts.append(Part(sort_order=i, quantity=p.get("quantity", 1), **{k: v for k, v in p.items() if k != "quantity"}))

    project = Project(
        name=name,
        slug=unique_slug(session, name),
        description=description,
        template=template,
        requirements=requirements.model_dump(),
        assumed_fields=assumed,
        parts=parts,
    )
    session.add(project)
    session.commit()
    if template:
        from app.services.costing import default_items

        session.add_all(default_items(project))
        session.commit()
    session.refresh(project)
    return project
