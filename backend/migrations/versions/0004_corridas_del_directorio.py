"""corridas del directorio

Registra cada extracción de la página de la Policía. La tabla nace con RLS para que
la API pública de Supabase no la exponga.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

import bandit.shared.db

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TABLES = ("directory_sync_runs",)


def upgrade() -> None:
    op.create_table(
        "directory_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trigger", sa.String(length=20), nullable=False),
        sa.Column("started_at", bandit.shared.db.UtcDateTime(timezone=True), nullable=False),
        sa.Column("finished_at", bandit.shared.db.UtcDateTime(timezone=True), nullable=True),
        sa.Column("published", sa.Integer(), nullable=False),
        sa.Column("rejected", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("error", sa.String(length=300), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("directory_sync_runs", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_directory_sync_runs_started_at"), ["started_at"], unique=False
        )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE directory_sync_runs ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    with op.batch_alter_table("directory_sync_runs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_directory_sync_runs_started_at"))
    op.drop_table("directory_sync_runs")
