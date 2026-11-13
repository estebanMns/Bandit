"""archivos del directorio

Fotos y volantes del directorio guardados en la base de datos, para que no dependan
del disco de cada equipo. La tabla nace con RLS para que la API pública de Supabase
no la exponga.

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

TABLES = ("directory_media",)


def upgrade() -> None:
    op.create_table(
        "directory_media",
        sa.Column("name", sa.String(length=320), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", bandit.shared.db.UtcDateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("directory_media")
