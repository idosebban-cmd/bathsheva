"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import bom, cad, costdown, costing, dfm, engineering, parts, projects, quotes, revisions
from app.config import settings
from app.db import init_db


def create_app() -> FastAPI:
    init_db(settings.database_url)
    app = FastAPI(title="Product Workbench", version="0.1.0")
    app.include_router(projects.router)
    app.include_router(parts.router)
    app.include_router(cad.router)
    app.include_router(engineering.router)
    app.include_router(bom.router)
    app.include_router(dfm.router)
    app.include_router(revisions.router)
    app.include_router(quotes.router)
    app.include_router(costing.router)
    app.include_router(costdown.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "llm_provider": settings.llm_provider}

    # Uploaded images and generated files, served read-only.
    projects_dir = settings.data_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/files/projects", StaticFiles(directory=projects_dir), name="files")
    return app


app = create_app()
