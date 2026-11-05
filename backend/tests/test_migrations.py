"""Toda tabla nueva debe entrar en la migración de RLS o quedaría expuesta en Supabase."""

import importlib.util
from pathlib import Path

import bandit.bootstrap  # noqa: F401  Registra todas las tablas.
from bandit.shared.db import Base

MIGRATION = Path(__file__).parent.parent / "migrations/versions/0003_activar_rls_en_postgres.py"


def test_every_table_has_row_level_security() -> None:
    spec = importlib.util.spec_from_file_location("rls_migration", MIGRATION)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert set(Base.metadata.tables) <= set(migration.TABLES)
