"""External supplier quotes per part, and the quoting pack export."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_project
from app.config import settings
from app.db import get_session
from app.models import ExternalQuote, Part, Project, Revision
from app.services.costing import build_inputs, model_part_estimate, reference_quantity
from app.services.quotes import QuotePackError, build_quote_pack, estimate_for, quote_dict

router = APIRouter(prefix="/api/projects/{project_id}", tags=["quotes"])

ALLOWED_ATTACHMENTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".csv", ".xlsx", ".xls", ".docx", ".eml", ".msg"}


def _part(project: Project, part_id: int, session: Session) -> Part:
    part = session.get(Part, part_id)
    if part is None or part.project_id != project.id:
        raise HTTPException(404, "Part not found")
    return part


def _revision_numbers(project: Project) -> dict[int, int]:
    return {r.id: r.number for r in project.revisions}


def _model_estimator(project: Project, part: Part, session: Session):
    """Cost-model estimate for this part at a given piece quantity (None if the model can't cost it)."""
    if part.cost_low is not None or part.cost_high is not None:
        return None  # manual values take priority; skip building the model
    inputs, _ = build_inputs(session, project)
    if not any(p.part_id == part.id for p in inputs.parts):
        return None
    return lambda qty: model_part_estimate(inputs, part, qty)


@router.get("/parts/{part_id}/quotes")
def list_quotes(part_id: int, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    part = _part(project, part_id, session)
    model = _model_estimator(project, part, session)
    ref_q, _ = reference_quantity(project)
    estimate = estimate_for(part, model, ref_q * part.quantity)
    revs = _revision_numbers(project)
    quotes = session.scalars(
        select(ExternalQuote).where(ExternalQuote.part_id == part.id).order_by(ExternalQuote.quote_date.desc(), ExternalQuote.id.desc())
    ).all()
    return {
        "part_id": part.id,
        "estimate": estimate,
        # Model estimates depend on quantity (setup and tooling are shared), so each quote is
        # compared with the model at that quote's quantity.
        "quotes": [quote_dict(q, estimate_for(part, model, q.quantity), revs.get(q.revision_id)) for q in quotes],
        "note": "Quotes are for your review only. They do not change the rules engine or seed data.",
    }


@router.post("/parts/{part_id}/quotes", status_code=201)
def add_quote(
    part_id: int,
    source: str = Form(...),
    quote_date: date = Form(...),
    quantity: int = Form(...),
    unit_price: float = Form(...),
    currency: str = Form("GBP"),
    process: str = Form(""),
    material: str = Form(""),
    finish: str = Form(""),
    lead_time_days: int | None = Form(None),
    dfm_notes: str = Form(""),
    revision_id: int | None = Form(None),
    attachment: UploadFile | None = File(None),
    project: Project = Depends(get_project),
    session: Session = Depends(get_session),
):
    part = _part(project, part_id, session)
    if not source.strip():
        raise HTTPException(422, "Source is required (e.g. 'Xometry')")
    if quantity < 1:
        raise HTTPException(422, "Quantity must be at least 1")
    if unit_price < 0:
        raise HTTPException(422, "Unit price cannot be negative")
    currency = currency.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise HTTPException(422, "Currency must be a 3-letter code such as GBP, EUR or USD")
    if lead_time_days is not None and lead_time_days < 0:
        raise HTTPException(422, "Lead time cannot be negative")
    if revision_id is not None:
        rev = session.get(Revision, revision_id)
        if rev is None or rev.project_id != project.id:
            raise HTTPException(422, "Revision does not belong to this project")

    quote = ExternalQuote(
        project_id=project.id, part_id=part.id, revision_id=revision_id, source=source.strip(),
        quote_date=quote_date, process=process.strip(), material=material.strip(), finish=finish.strip(),
        quantity=quantity, unit_price=unit_price, currency=currency, lead_time_days=lead_time_days,
        dfm_notes=dfm_notes.strip(),
    )
    if attachment is not None and attachment.filename:
        suffix = Path(attachment.filename).suffix.lower()
        if suffix not in ALLOWED_ATTACHMENTS:
            raise HTTPException(422, f"Unsupported attachment type {suffix!r}")
        rel = Path("projects") / str(project.id) / "quotes" / f"{uuid.uuid4().hex}{suffix}"
        dest = settings.data_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(attachment.file.read())
        quote.attachment_path = rel.as_posix()
        quote.attachment_filename = attachment.filename
    session.add(quote)
    session.commit()
    model = _model_estimator(project, part, session)
    return quote_dict(quote, estimate_for(part, model, quantity), _revision_numbers(project).get(revision_id))


@router.delete("/quotes/{quote_id}", status_code=204)
def delete_quote(quote_id: int, project: Project = Depends(get_project), session: Session = Depends(get_session)):
    quote = session.get(ExternalQuote, quote_id)
    if quote is None or quote.project_id != project.id:
        raise HTTPException(404, "Quote not found")
    if quote.attachment_path:
        (settings.data_dir / quote.attachment_path).unlink(missing_ok=True)
    session.delete(quote)
    session.commit()


@router.get("/quote-pack.zip")
def quote_pack(project: Project = Depends(get_project)):
    try:
        filename, data = build_quote_pack(project)
    except QuotePackError as e:
        raise HTTPException(409, str(e)) from e
    return Response(data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
