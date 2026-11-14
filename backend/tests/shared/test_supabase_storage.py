"""Archivos compartidos en Supabase Storage: subir, leer, borrar y purgar evidencia vieja."""

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
import respx

from bandit.directory.infrastructure.supabase_media import SupabaseMediaStore
from bandit.incidents.infrastructure.supabase_evidence import SupabaseEvidenceStore
from bandit.shared.supabase_storage import SupabaseStorage

BASE = "https://proyecto.supabase.co/storage/v1/object"


def storage() -> SupabaseStorage:
    return SupabaseStorage("https://proyecto.supabase.co/", "clave-servicio", "bandit")


@respx.mock
async def test_evidence_is_uploaded_privately_and_read_back():
    incident = uuid4()
    upload = respx.post(f"{BASE}/bandit/evidence/{incident}.jpg").mock(
        return_value=httpx.Response(200, json={"Key": "ok"})
    )
    respx.get(f"{BASE}/bandit/evidence/{incident}.jpg").mock(
        return_value=httpx.Response(200, content=b"jpeg")
    )
    store = SupabaseEvidenceStore(storage())

    await store.save(incident, b"jpeg")

    sent = upload.calls[0].request
    assert sent.headers["authorization"] == "Bearer clave-servicio"
    assert sent.headers["content-type"] == "image/jpeg"
    assert sent.headers["x-upsert"] == "true"
    assert await store.load(incident) == b"jpeg"


@respx.mock
@pytest.mark.parametrize("status", [400, 404])
async def test_missing_evidence_is_none(status):
    incident = uuid4()
    respx.get(f"{BASE}/bandit/evidence/{incident}.jpg").mock(
        return_value=httpx.Response(status, json={"error": "not_found"})
    )

    assert await SupabaseEvidenceStore(storage()).load(incident) is None


@respx.mock
async def test_purge_deletes_only_evidence_older_than_the_cutoff():
    respx.post(f"{BASE}/list/bandit").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "1", "name": "vieja.jpg", "created_at": "2026-11-01T10:00:00Z"},
                {"id": "2", "name": "nueva.jpg", "created_at": "2026-11-13T10:00:00Z"},
            ],
        )
    )
    delete = respx.delete(f"{BASE}/bandit").mock(return_value=httpx.Response(200, json=[]))

    removed = await SupabaseEvidenceStore(storage()).purge_older_than(
        datetime(2026, 11, 10, tzinfo=UTC)
    )

    assert removed == 1
    assert b"evidence/vieja.jpg" in delete.calls[0].request.content
    assert b"nueva" not in delete.calls[0].request.content


@respx.mock
async def test_directory_media_rejects_paths_and_reads_by_name():
    respx.get(f"{BASE}/bandit/directory/ana.jpg").mock(
        return_value=httpx.Response(200, content=b"foto")
    )
    media = SupabaseMediaStore(storage())

    assert await media.load("ana.jpg") == b"foto"
    assert await media.load("../secreto") is None
    with pytest.raises(ValueError):
        await media.save("../secreto.jpg", b"x")
