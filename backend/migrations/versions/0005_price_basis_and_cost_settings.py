"""price basis on cost items and project cost settings

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-06 09:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cost_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('price_basis', sa.String(length=30), nullable=False,
                                      server_default='model_estimate'))
        batch_op.add_column(sa.Column('basis_quantity', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('discount_class', sa.String(length=50), nullable=True))
        batch_op.alter_column('source', existing_type=sa.String(length=300), type_=sa.Text(),
                              existing_nullable=False)
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cost_settings', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('cost_settings')
    with op.batch_alter_table('cost_items', schema=None) as batch_op:
        batch_op.alter_column('source', existing_type=sa.Text(), type_=sa.String(length=300),
                              existing_nullable=False)
        batch_op.drop_column('discount_class')
        batch_op.drop_column('basis_quantity')
        batch_op.drop_column('price_basis')
