"""Pruebas de punta a punta de la capa HTTP: sesión, CSRF, permisos y secretos."""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.websockets import WebSocketDisconnect

from bandit.main import create_app
from bandit.shared.config import Settings
from bandit.shared.db import Base

ADMIN = "admin@example.com"
PASSWORD = "clave-segura-de-prueba"
RTSP_URL = "rtsp://usuario:secreto@10.0.0.9/stream"


async def _create_schema(url: str) -> None:
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'api.db'}"
    settings = Settings(
        _env_file=None,
        database_url=url,
        camera_encryption_key=Fernet.generate_key().decode(),
        bootstrap_admin_email=ADMIN,
        bootstrap_admin_password=PASSWORD,
        ffmpeg_path="ffmpeg-inexistente",
        media_root=str(tmp_path),
    )
    app = create_app(settings)
    asyncio.run(_create_schema(url))
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str = ADMIN) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies["bandit_csrf"]}


def create_local(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/establishments", json={"name": "Bar", "address": "Calle 1"}, headers=headers
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_protected_routes_require_a_session(client: TestClient) -> None:
    assert client.get("/api/establishments").status_code == 401


def test_session_cookie_is_http_only(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": ADMIN, "password": PASSWORD})

    cookies = response.headers.get_list("set-cookie")
    session = next(cookie for cookie in cookies if cookie.startswith("bandit_session="))
    assert "HttpOnly" in session
    assert "SameSite=lax" in session


def test_changes_require_the_csrf_token(client: TestClient) -> None:
    login(client)

    response = client.post("/api/establishments", json={"name": "Bar", "address": "Calle 1"})

    assert response.status_code == 403


def test_camera_url_never_appears_in_responses(client: TestClient) -> None:
    headers = login(client)
    local = create_local(client, headers)

    created = client.post(
        f"/api/establishments/{local}/cameras",
        json={"name": "Barra", "url": RTSP_URL},
        headers=headers,
    )
    listed = client.get(f"/api/establishments/{local}/cameras")

    assert created.status_code == 201
    assert "secreto" not in created.text
    assert "secreto" not in listed.text


def test_invalid_camera_url_is_rejected(client: TestClient) -> None:
    headers = login(client)
    local = create_local(client, headers)

    response = client.post(
        f"/api/establishments/{local}/cameras",
        json={"name": "Barra", "url": "http://10.0.0.9/stream"},
        headers=headers,
    )

    assert response.status_code == 422


def test_operator_cannot_reach_another_establishment(client: TestClient) -> None:
    headers = login(client)
    own, other = create_local(client, headers), create_local(client, headers)
    created = client.post(
        "/api/auth/users",
        json={"email": "op@example.com", "password": PASSWORD, "establishment_id": own},
        headers=headers,
    )
    assert created.status_code == 201

    client.cookies.clear()
    headers = login(client, "op@example.com")

    assert client.get(f"/api/establishments/{own}").status_code == 200
    assert client.get(f"/api/establishments/{other}").status_code == 403
    assert client.get(f"/api/establishments/{other}/incidents").status_code == 403
    assert [local["id"] for local in client.get("/api/establishments").json()] == [own]
    assert (
        client.put(
            f"/api/establishments/{other}/cai-whatsapp",
            json={"number": "+573001234567"},
            headers=headers,
        ).status_code
        == 403
    )


def test_operator_cannot_register_cameras(client: TestClient) -> None:
    headers = login(client)
    local = create_local(client, headers)
    client.post(
        "/api/auth/users",
        json={"email": "op@example.com", "password": PASSWORD, "establishment_id": local},
        headers=headers,
    )
    client.cookies.clear()
    headers = login(client, "op@example.com")

    response = client.post(
        f"/api/establishments/{local}/cameras",
        json={"name": "Barra", "url": RTSP_URL},
        headers=headers,
    )

    assert response.status_code == 403


def test_events_socket_sends_sync_to_authorized_clients(client: TestClient) -> None:
    headers = login(client)
    local = create_local(client, headers)

    with client.websocket_connect(f"/ws/events/{local}") as socket:
        assert socket.receive_json() == {"type": "sync"}


def test_events_socket_rejects_anonymous_clients(client: TestClient) -> None:
    headers = login(client)
    local = create_local(client, headers)
    client.cookies.clear()

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/events/{local}"):
        pass


def test_sockets_reject_foreign_origins(client: TestClient) -> None:
    headers = login(client)
    local = create_local(client, headers)

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/ws/events/{local}", headers={"Origin": "https://sitio-malicioso.example"}
        ),
    ):
        pass


def test_video_socket_rejects_unknown_cameras(client: TestClient) -> None:
    login(client)

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/video/{uuid4()}"):
        pass
