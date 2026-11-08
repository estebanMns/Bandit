"""Toda tabla nueva debe activar RLS en una migración o quedaría expuesta en Supabase."""

import importlib.util
from pathlib import Path

import bandit.bootstrap  # noqa: F401  Registra todas las tablas.
from bandit.shared.db import Base

VERSIONS = Path(__file__).parent.parent / "migrations/versions"


def _tables_with_rls() -> set[str]:
    """Une la lista TABLES de cada migración que activa RLS."""
    tables: set[str] = set()
    for path in sorted(VERSIONS.glob("*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        assert spec is not None and spec.loader is not None
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        tables |= set(getattr(migration, "TABLES", ()))
    return tables


def test_every_table_has_row_level_security() -> None:
    assert set(Base.metadata.tables) <= _tables_with_rls()
