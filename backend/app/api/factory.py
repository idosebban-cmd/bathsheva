"""Factory Pack tab: RFQ pack with drawings, RFQ document, STEP files and BOM."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from fastapi.responses import Response

from app.api.deps import get_project
from app.models import Project
from app.services import factory_pack as fp

router = APIRouter(prefix="/api/projects/{project_id}", tags=["factory"])


def _contents(project: Project):
    try:
        return fp.pack_contents(project)
    except fp.FactoryPackError as e:
        raise HTTPException(409, str(e)) from e


@router.get("/factory-pack")
def summary(project: Project = Depends(get_project)):
    try:
        return fp.pack_summary(project)
    except fp.FactoryPackError as e:
        raise HTTPException(409, str(e)) from e


@router.get("/factory-pack.zip")
def pack_zip(project: Project = Depends(get_project)):
    try:
        filename, data = fp.build_factory_pack(project)
    except fp.FactoryPackError as e:
        raise HTTPException(409, str(e)) from e
    return Response(data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/drawings/{cad_key}.{fmt}")
def drawing(cad_key: str, fmt: str, project: Project = Depends(get_project)):
    if fmt not in ("svg", "pdf"):
        raise HTTPException(404, "Drawings are available as .svg or .pdf")
    c = _contents(project)
    try:
        svg, pdf = fp.drawing_files(c, cad_key)
    except fp.FactoryPackError as e:
        raise HTTPException(404, str(e)) from e
    name = f"{project.slug}_{cad_key}_drawing.{fmt}"
    if fmt == "svg":
        return Response(svg, media_type="image/svg+xml", headers={"Content-Disposition": f'inline; filename="{name}"'})
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{name}"'})


@router.get("/rfq.{fmt}")
def rfq(fmt: str, project: Project = Depends(get_project)):
    blocks = fp.rfq_blocks(_contents(project))
    if fmt == "md":
        return Response(fp.rfq_markdown(blocks), media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="{project.slug}_rfq.md"'})
    if fmt == "pdf":
        return Response(fp.rfq_pdf(blocks), media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{project.slug}_rfq.pdf"'})
    raise HTTPException(404, "RFQ is available as .md or .pdf")


@router.get("/rfq-electronics.{fmt}")
def rfq_electronics(fmt: str, project: Project = Depends(get_project)):
    blocks = fp.electronics_rfq_blocks(_contents(project))
    if fmt == "md":
        return Response(fp.rfq_markdown(blocks), media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="{project.slug}_rfq_electronics.md"'})
    if fmt == "pdf":
        return Response(fp.rfq_pdf(blocks, "Request for quotation: battery, control board and LEDs"),
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{project.slug}_rfq_electronics.pdf"'})
    raise HTTPException(404, "RFQ is available as .md or .pdf")


@router.get("/factory-pack/contact")
def get_contact(project: Project = Depends(get_project)):
    return {"values": fp.contact(project), "missing": fp.missing_contact(project)}


@router.put("/factory-pack/contact")
def put_contact(body: dict[str, str | None], project: Project = Depends(get_project), session: Session = Depends(get_session)):
    try:
        fp.update_contact(project, body)
    except fp.FactoryPackError as e:
        raise HTTPException(422, str(e)) from e
    session.commit()
    return {"values": fp.contact(project), "missing": fp.missing_contact(project)}
