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


# Template part keys that are not Part columns (template-only metadata).
TEMPLATE_ONLY_PART_KEYS = {"quantity", "made_to_drawing"}


def template_part(spec: dict, sort_order: int) -> Part:
    return Part(sort_order=sort_order, quantity=spec.get("quantity", 1),
                **{k: v for k, v in spec.items() if k not in TEMPLATE_ONLY_PART_KEYS})


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
            parts.append(template_part(p, i))

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
    _clear_stale_folder(project.id)
    if template:
        from app.services.costing import default_items

        session.add_all(default_items(project))
        session.commit()
        from app.services.decisions import apply_template_decisions

        session.refresh(project)
        apply_template_decisions(session, project)
    session.refresh(project)
    return project


def project_dir(project_id: int):
    """The project's own folder in the data folder (uploads, generated CAD and exports)."""
    from app.config import settings

    return settings.data_dir / "projects" / str(int(project_id))


def delete_project(session: Session, project: Project) -> None:
    """Delete the project's records (they cascade from the project) and then its files."""
    import shutil

    from app.config import settings

    folder = project_dir(project.id)
    root = (settings.data_dir / "projects").resolve()
    session.delete(session.merge(project))
    session.commit()
    if folder.resolve().parent == root and folder.exists():  # never anything outside data/projects/<id>
        shutil.rmtree(folder)


def _clear_stale_folder(project_id: int) -> None:
    """A new project must start with an empty data folder. SQLite can reuse the id of the last deleted
    project, so a folder left behind (an interrupted delete, or files from before deletes removed them) is
    moved aside to projects/_orphaned/ rather than inherited or destroyed."""
    import datetime as dt

    folder = project_dir(project_id)
    if folder.exists():
        dest = folder.parent / "_orphaned" / f"{project_id}-{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%S%f}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        folder.rename(dest)
