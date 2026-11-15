"""archivos del directorio

Las fotos y los volantes del directorio se guardan en la misma base de datos (Supabase), no en el
disco del servidor: el disco de Render se borra en cada despliegue y las fotos quedaban en 404.
Además se eliminan los registros que ya habían salido del listado de la Policía.
La tabla nace con RLS para que la API pública de Supabase no la exponga.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op

import bandit.shared.db

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

TABLES = ("directory_files",)


def upgrade() -> None:
    op.create_table(
        "directory_files",
        sa.Column("name", sa.String(length=320), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("updated_at", bandit.shared.db.UtcDateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE directory_files ENABLE ROW LEVEL SECURITY")
    # Quien ya no está en el listado de la Policía ahora se elimina en vez de ocultarse.
    op.execute(sa.text("DELETE FROM wanted_records WHERE active = :inactive").bindparams(inactive=False))


def downgrade() -> None:
    op.drop_table("directory_files")
