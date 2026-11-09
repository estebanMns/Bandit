"""prioridad del directorio

Guarda la recompensa en pesos y el orden de la página de la Policía para priorizar el
directorio, y cuántas páginas fallaron en cada extracción. Las tablas ya tienen RLS.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("wanted_records", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reward_amount", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("listing_position", sa.Integer(), nullable=True))
    with op.batch_alter_table("directory_sync_runs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("pages_failed", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("directory_sync_runs", schema=None) as batch_op:
        batch_op.drop_column("pages_failed")
    with op.batch_alter_table("wanted_records", schema=None) as batch_op:
        batch_op.drop_column("listing_position")
        batch_op.drop_column("reward_amount")
