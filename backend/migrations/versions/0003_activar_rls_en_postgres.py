"""activar RLS en postgres

Supabase publica el esquema `public` por su API. Sin políticas, RLS bloquea ese
acceso; Bandit no se ve afectado porque se conecta como dueño de las tablas.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLES = (
    "alembic_version",
    "cameras",
    "establishments",
    "incident_audit",
    "incidents",
    "push_targets",
    "sessions",
    "users",
    "wanted_records",
)


def _set_row_security(action: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} {action} ROW LEVEL SECURITY")


def upgrade() -> None:
    _set_row_security("ENABLE")


def downgrade() -> None:
    _set_row_security("DISABLE")
