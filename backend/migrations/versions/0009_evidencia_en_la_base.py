"""evidencia en la base

La foto de cada evento se guarda en la misma base de datos (Supabase) y vive mientras exista el
evento. Antes quedaba en el disco del equipo que lo detectó (el PC) y desde Vercel o Render salía
"La evidencia de este evento ya no está disponible"; además se borraba a los 7 días.
La tabla nace con RLS para que la API pública de Supabase no la exponga.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

import bandit.shared.db

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

TABLES = ("incident_evidence",)


def upgrade() -> None:
    op.create_table(
        "incident_evidence",
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("jpeg", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", bandit.shared.db.UtcDateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("incident_id"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE incident_evidence ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("incident_evidence")
