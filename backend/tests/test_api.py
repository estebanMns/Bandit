"""Pruebas de punta a punta de la capa HTTP: sesión, CSRF, permisos y secretos."""

import asyncio
import time
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


def test_login_accepts_internal_domains(tmp_path: Path) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path / 'interno.db'}"
    app = create_app(
        Settings(
            _env_file=None,
            database_url=url,
            camera_encryption_key=Fernet.generate_key().decode(),
            bootstrap_admin_email="admin@bandit.local",
            bootstrap_admin_password=PASSWORD,
            media_root=str(tmp_path),
        )
    )
    asyncio.run(_create_schema(url))

    with TestClient(app) as client:
        assert login(client, "admin@bandit.local")


def test_wrong_credentials_get_a_readable_error(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": "no-es-correo", "password": "x"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Correo o clave incorrectos"


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


def register(client: TestClient, email: str, local: str = "Bar") -> dict[str, str]:
    client.cookies.clear()
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "local_name": local,
            "local_address": "Calle 1",
        },
    )
    assert response.status_code == 201, response.text
    # El registro no abre sesión: se ingresa como lo haría la persona.
    assert "bandit_session" not in response.cookies
    return login(client, email)


def only_local(client: TestClient) -> str:
    return client.get("/api/establishments").json()[0]["id"]


def test_register_logs_in_as_owner_of_a_new_local(client: TestClient) -> None:
    register(client, "duena@example.com", "La Esquina")

    assert client.get("/api/auth/me").json()["role"] == "owner"
    assert [local["name"] for local in client.get("/api/establishments").json()] == ["La Esquina"]


def test_register_ignores_a_requested_role(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "intruso@example.com",
            "password": PASSWORD,
            "local_name": "Bar",
            "local_address": "Calle 1",
            "role": "admin",
        },
    )

    assert response.json()["role"] == "owner"


def test_register_rejects_a_repeated_email(client: TestClient) -> None:
    register(client, "duena@example.com")

    response = client.post(
        "/api/auth/register",
        json={
            "email": "DUENA@example.com",
            "password": PASSWORD,
            "local_name": "Otro",
            "local_address": "Calle 2",
        },
    )

    assert response.status_code == 409


def test_register_explains_a_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "duena@example.com",
            "password": "corta",
            "local_name": "Bar",
            "local_address": "Calle 1",
        },
    )

    assert response.status_code == 422
    assert "12 caracteres" in response.json()["detail"]


def test_register_is_rate_limited(client: TestClient) -> None:
    for number in range(5):
        register(client, f"u{number}@example.com")

    response = client.post(
        "/api/auth/register",
        json={
            "email": "u9@example.com",
            "password": PASSWORD,
            "local_name": "Bar",
            "local_address": "Calle 1",
        },
    )

    assert response.status_code == 429


def test_owner_manages_own_cameras(client: TestClient) -> None:
    headers = register(client, "duena@example.com")
    local = only_local(client)

    created = client.post(
        f"/api/establishments/{local}/cameras",
        json={"name": "Barra", "url": RTSP_URL},
        headers=headers,
    )
    camera = created.json()["id"]

    assert created.status_code == 201
    assert (
        client.patch(f"/api/cameras/{camera}", json={"enabled": False}, headers=headers).status_code
        == 200
    )
    assert client.delete(f"/api/cameras/{camera}", headers=headers).status_code == 204


def test_owners_cannot_touch_each_other(client: TestClient) -> None:
    victim_headers = register(client, "victima@example.com", "Ajeno")
    victim_local = only_local(client)
    camera = client.post(
        f"/api/establishments/{victim_local}/cameras",
        json={"name": "Barra", "url": RTSP_URL},
        headers=victim_headers,
    ).json()["id"]

    headers = register(client, "intruso@example.com", "Propio")

    assert victim_local not in [local["id"] for local in client.get("/api/establishments").json()]
    for response in (
        client.get(f"/api/establishments/{victim_local}"),
        client.get(f"/api/establishments/{victim_local}/cameras"),
        client.get(f"/api/establishments/{victim_local}/incidents"),
        client.post(
            f"/api/establishments/{victim_local}/cameras",
            json={"name": "Espía", "url": RTSP_URL},
            headers=headers,
        ),
        client.patch(f"/api/cameras/{camera}", json={"enabled": False}, headers=headers),
        client.delete(f"/api/cameras/{camera}", headers=headers),
        client.put(
            f"/api/establishments/{victim_local}/cai-whatsapp",
            json={"number": "+573001234567"},
            headers=headers,
        ),
        client.post(f"/api/establishments/{victim_local}/whatsapp-test", headers=headers),
    ):
        assert response.status_code == 403, response.request.url

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/video/{camera}"):
        pass
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/events/{victim_local}"):
        pass


def test_owner_has_no_global_powers(client: TestClient) -> None:
    headers = register(client, "duena@example.com")

    assert (
        client.post(
            "/api/establishments", json={"name": "Otro", "address": "Calle"}, headers=headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/users",
            json={"email": "x@example.com", "password": PASSWORD, "role": "admin"},
            headers=headers,
        ).status_code
        == 403
    )


def test_activity_panel_starts_empty_for_the_owner(client: TestClient) -> None:
    register(client, "panel@example.com")
    local = only_local(client)

    response = client.get(f"/api/establishments/{local}/analysis-activity")

    assert response.status_code == 200
    body = response.json()
    assert body["cameras"] == []
    assert body["budget"]["used"] == 0
    assert body["model_enabled"] is False


def test_activity_panel_is_private_to_each_local(client: TestClient) -> None:
    register(client, "uno@example.com", "Uno")
    first = only_local(client)
    register(client, "dos@example.com", "Dos")

    assert client.get(f"/api/establishments/{first}/analysis-activity").status_code == 403
    assert client.get(f"/api/analysis/cameras/{uuid4()}/last-frame").status_code == 404


def wait_for_idle_directory(client: TestClient) -> dict[str, object]:
    for _ in range(50):
        status = client.get("/api/directory/sync-runs").json()
        if not status["running"]:
            return status
        time.sleep(0.05)
    raise AssertionError("La extracción no terminó")


def test_directory_extraction_runs_at_startup_and_limits_manual_runs(
    client: TestClient,
) -> None:
    headers = register(client, "dueno-directorio@example.com")

    status = wait_for_idle_directory(client)
    assert [run["trigger"] for run in status["runs"]] == ["startup"]
    assert client.post("/api/directory/sync", headers=headers).status_code == 429


def test_directory_status_requires_a_session(client: TestClient) -> None:
    assert client.get("/api/directory/sync-runs").status_code == 401


def demo_client(tmp_path: Path, demo: bool) -> TestClient:
    url = f"sqlite+aiosqlite:///{tmp_path / 'demo.db'}"
    settings = Settings(
        _env_file=None,
        database_url=url,
        camera_encryption_key=Fernet.generate_key().decode(),
        ffmpeg_path="ffmpeg-inexistente",
        media_root=str(tmp_path),
        demo_admin=demo,
    )
    if not (tmp_path / "demo.db").exists():
        asyncio.run(_create_schema(url))
    return TestClient(create_app(settings))


def demo_login(client: TestClient) -> int:
    return client.post("/api/auth/login", json={"email": "admin", "password": "admin"}).status_code


def test_demo_account_exists_only_while_enabled(tmp_path: Path) -> None:
    with demo_client(tmp_path, demo=True) as client:
        assert client.get("/api/auth/options").json() == {"demo": True}
        assert demo_login(client) == 200
        assert client.get("/api/auth/me").json()["role"] == "admin"

    with demo_client(tmp_path, demo=False) as client:
        assert client.get("/api/auth/options").json() == {"demo": False}
        assert demo_login(client) == 401


def test_open_registration_still_requires_long_passwords(tmp_path: Path) -> None:
    with demo_client(tmp_path, demo=True) as client:
        response = client.post(
            "/api/auth/register",
            json={
                "email": "corta@example.com",
                "password": "admin",
                "local_name": "Bar",
                "local_address": "Calle 1",
            },
        )
        assert response.status_code == 422


def test_logout_ends_the_session_at_once(client: TestClient) -> None:
    headers = register(client, "salida@example.com")
    assert client.get("/api/auth/me").status_code == 200
    token = client.cookies.get("bandit_session")

    assert client.post("/api/auth/logout", headers=headers).status_code in (200, 204)

    client.cookies.set("bandit_session", token)
    assert client.get("/api/auth/me").status_code == 401


def test_registration_asks_to_log_in_afterwards(client: TestClient) -> None:
    client.cookies.clear()
    response = client.post(
        "/api/auth/register",
        json={
            "email": "nueva@example.com",
            "password": PASSWORD,
            "local_name": "Bar",
            "local_address": "Calle 1",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "owner"
    assert client.get("/api/auth/me").status_code == 401
    login(client, "nueva@example.com")
    assert client.get("/api/auth/me").json()["role"] == "owner"


def test_location_and_map_require_a_session_and_stay_in_narino(client: TestClient) -> None:
    assert client.get("/api/map/tiles/13/2335/4068.png").status_code == 401
    assert client.get("/api/places/nearby-cai?lat=1.21&lng=-77.28").status_code == 401

    headers = register(client, "mapa@example.com")
    local = only_local(client)
    response = client.put(
        f"/api/establishments/{local}/location",
        json={"latitude": 1.2136, "longitude": -77.2811},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["latitude"] == 1.2136
    assert client.get("/api/places/nearby-cai?lat=4.71&lng=-74.07").status_code == 422
    assert client.get("/api/map/tiles/13/2390/3960.png").status_code == 404
