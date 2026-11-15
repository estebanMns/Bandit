"""camaras imou por local

Registra a qué local pertenece cada cámara Imou, por su número de serie: la cuenta de Imou de
Bandit es una sola para todos los clientes y ningún local debe ver las cámaras de otro.
La tabla nace con RLS para que la API pública de Supabase no la exponga.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

import bandit.shared.db

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

TABLES = ("imou_devices",)


def upgrade() -> None:
    op.create_table(
        "imou_devices",
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", bandit.shared.db.UtcDateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("device_id"),
    )
    with op.batch_alter_table("imou_devices", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_imou_devices_establishment_id"), ["establishment_id"], unique=False
        )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE imou_devices ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    with op.batch_alter_table("imou_devices", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_imou_devices_establishment_id"))
    op.drop_table("imou_devices")
