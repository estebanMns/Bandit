"""Sube a Supabase Storage las imágenes guardadas en el disco de este backend.

Sirve una vez, al pasar a producción: la evidencia de los eventos y las fotos del directorio que
se guardaron en el disco de un equipo (por ejemplo el Docker de un PC) quedan disponibles para
todos los backends, incluido el de la nube. No borra nada del disco.

Uso, dentro del contenedor del backend y con SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY definidas:

    python -m bandit.tools.upload_media

Con ``--db`` copia las fotos y volantes del directorio a la tabla ``directory_files`` de la base
(DATABASE_URL), que es donde ahora los busca Bandit. No necesita Supabase Storage:

    python -m bandit.tools.upload_media --db
"""

import asyncio
import sys
from pathlib import Path
from typing import Protocol

from bandit.shared.supabase_storage import SupabaseStorage

_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}
# Carpeta del disco → carpeta en Storage, las mismas que usan los adaptadores.
FOLDERS = ("evidence", "directory")


async def upload_folder(storage: SupabaseStorage, root: Path, folder: str) -> tuple[int, int]:
    """Devuelve (subidos, fallidos). Solo archivos con extensión conocida, sin subcarpetas."""
    uploaded = failed = 0
    source = root / folder
    if not source.is_dir():
        return 0, 0
    for path in sorted(source.iterdir()):
        content_type = _TYPES.get(path.suffix.lower())
        if not path.is_file() or content_type is None:
            continue
        try:
            await storage.upload(f"{folder}/{path.name}", path.read_bytes(), content_type)
            uploaded += 1
        except Exception as error:
            print(f"  no se pudo subir {folder}/{path.name}: {type(error).__name__}")
            failed += 1
    return uploaded, failed


class FileSink(Protocol):
    async def save(self, name: str, data: bytes, source: str | None = None) -> None: ...


async def copy_directory_files(sink: FileSink, root: Path) -> tuple[int, int]:
    """Copia la carpeta ``directory`` del disco a la base. Devuelve (copiados, fallidos)."""
    copied = failed = 0
    source = root / "directory"
    if not source.is_dir():
        return 0, 0
    for path in sorted(source.iterdir()):
        if not path.is_file() or path.suffix.lower() not in _TYPES:
            continue
        try:
            await sink.save(path.name, path.read_bytes())
            copied += 1
        except Exception as error:
            print(f"  no se pudo copiar {path.name}: {type(error).__name__}")
            failed += 1
    return copied, failed


async def _to_database() -> int:
    from bandit.directory.infrastructure.db_media import DbMediaStore
    from bandit.shared.config import get_settings
    from bandit.shared.db import create_engine, create_session_factory

    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        copied, failed = await copy_directory_files(
            DbMediaStore(create_session_factory(engine)), Path(settings.media_root)
        )
    finally:
        await engine.dispose()
    print(f"directory → base de datos: {copied} copiados, {failed} con error")
    return 1 if failed else 0


async def _main() -> int:
    from bandit.shared.config import get_settings

    if "--db" in sys.argv[1:]:
        return await _to_database()
    settings = get_settings()
    if not (settings.supabase_url and settings.supabase_service_role_key):
        print("Faltan SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY.")
        return 1
    storage = SupabaseStorage(
        settings.supabase_url, settings.supabase_service_role_key, settings.supabase_storage_bucket
    )
    root = Path(settings.media_root)
    total_failed = 0
    for folder in FOLDERS:
        uploaded, failed = await upload_folder(storage, root, folder)
        total_failed += failed
        print(f"{folder}: {uploaded} subidos, {failed} con error")
    return 1 if total_failed else 0


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
