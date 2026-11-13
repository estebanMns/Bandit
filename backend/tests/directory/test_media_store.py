"""Fotos del directorio en la base: compresión, caché e importación desde el disco viejo."""

from io import BytesIO

from PIL import Image

from bandit.directory.application.media_import import import_disk_media
from bandit.directory.infrastructure.db_media import DbMediaStore, _shrink


def _png(width: int, height: int) -> bytes:
    out = BytesIO()
    Image.new("RGBA", (width, height), (200, 30, 30, 255)).save(out, format="PNG")
    return out.getvalue()


def test_large_photo_is_reduced_to_the_display_size():
    original = _png(2400, 1600)

    shrunk = _shrink("persona.png", original)

    with Image.open(BytesIO(shrunk)) as image:
        assert max(image.size) <= 640
        assert image.format == "PNG"
    assert len(shrunk) < len(original)


def test_undecodable_bytes_are_kept_as_they_are():
    assert _shrink("persona.jpg", b"no-es-una-imagen") == b"no-es-una-imagen"


def test_pdf_flyers_are_never_touched():
    pdf = b"%PDF-1.4 contenido"
    assert _shrink("persona-volante.pdf", pdf) == pdf


async def test_store_round_trip_and_cache_invalidation(sessions):
    store = DbMediaStore(sessions)
    await store.save("ana-ejemplo.png", _png(300, 300))

    first = await store.read("ana-ejemplo.png")
    assert first is not None and first.content_type == "image/png"

    await store.save("ana-ejemplo.png", _png(100, 100))
    second = await store.read("ana-ejemplo.png")
    assert second is not None and second.data != first.data

    await store.delete("ana-ejemplo.png")
    assert await store.read("ana-ejemplo.png") is None


async def test_import_copies_only_referenced_files_once(sessions, tmp_path):
    store = DbMediaStore(sessions)
    (tmp_path / "ana-ejemplo.jpg").write_bytes(b"foto-vieja")
    (tmp_path / "retirada.jpg").write_bytes(b"ya-no-es-activa")

    imported = await import_disk_media(
        tmp_path, store, ["ana-ejemplo.jpg", "ana-ejemplo.jpg", "sin-archivo.jpg", "../fuera.jpg"]
    )

    assert imported == 1
    assert await store.read("retirada.jpg") is None
    assert await import_disk_media(tmp_path, store, ["ana-ejemplo.jpg"]) == 0
