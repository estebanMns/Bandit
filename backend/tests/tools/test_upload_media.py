"""Subir al almacenamiento compartido lo que quedó en el disco de un equipo."""

import httpx
import respx

from bandit.shared.supabase_storage import SupabaseStorage
from bandit.tools.upload_media import upload_folder

BASE = "https://proyecto.supabase.co/storage/v1/object/bandit"


@respx.mock
async def test_uploads_known_files_and_skips_the_rest(tmp_path):
    folder = tmp_path / "directory"
    folder.mkdir()
    (folder / "ana.jpg").write_bytes(b"foto")
    (folder / "ana-volante.pdf").write_bytes(b"pdf")
    (folder / "notas.txt").write_text("no")
    photo = respx.post(f"{BASE}/directory/ana.jpg").mock(return_value=httpx.Response(200))
    flyer = respx.post(f"{BASE}/directory/ana-volante.pdf").mock(return_value=httpx.Response(200))
    storage = SupabaseStorage("https://proyecto.supabase.co", "clave", "bandit")

    uploaded, failed = await upload_folder(storage, tmp_path, "directory")

    assert (uploaded, failed) == (2, 0)
    assert photo.calls[0].request.headers["content-type"] == "image/jpeg"
    assert flyer.calls[0].request.headers["content-type"] == "application/pdf"


@respx.mock
async def test_a_failed_upload_is_counted_and_the_rest_continue(tmp_path):
    folder = tmp_path / "evidence"
    folder.mkdir()
    (folder / "a.jpg").write_bytes(b"1")
    (folder / "b.jpg").write_bytes(b"2")
    respx.post(f"{BASE}/evidence/a.jpg").mock(return_value=httpx.Response(500))
    respx.post(f"{BASE}/evidence/b.jpg").mock(return_value=httpx.Response(200))
    storage = SupabaseStorage("https://proyecto.supabase.co", "clave", "bandit")

    assert await upload_folder(storage, tmp_path, "evidence") == (1, 1)


async def test_a_missing_folder_uploads_nothing(tmp_path):
    storage = SupabaseStorage("https://proyecto.supabase.co", "clave", "bandit")

    assert await upload_folder(storage, tmp_path, "evidence") == (0, 0)
