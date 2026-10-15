"""Rename the product Atelier to Orbit (data only, no schema change)

Projects created from the template store its key in projects.template, and their CAD versions store the
generator in cad_models.generator: both move from "atelier" to "orbit". The product-ideas.md pendant that
was called Orbit is now Globe, so concepts opened from it (concepts.based_on, the concept's key) move from
"orbit" to "globe" first, before any speaker data takes the name.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-15 12:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE concepts SET based_on = 'globe' WHERE based_on = 'orbit'")
    op.execute("UPDATE projects SET template = 'orbit' WHERE template = 'atelier'")
    op.execute("UPDATE cad_models SET generator = 'orbit' WHERE generator = 'atelier'")


def downgrade() -> None:
    op.execute("UPDATE cad_models SET generator = 'atelier' WHERE generator = 'orbit'")
    op.execute("UPDATE projects SET template = 'atelier' WHERE template = 'orbit'")
    op.execute("UPDATE concepts SET based_on = 'orbit' WHERE based_on = 'globe'")
