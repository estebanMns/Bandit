"""Repositorios SQL de cámaras."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from bandit.cameras.domain.models import Camera
from bandit.cameras.infrastructure.tables import CameraRow, ImouDeviceRow
from bandit.shared.db import SessionFactory
from bandit.shared.errors import ConflictError


def _to_model(row: CameraRow) -> Camera:
    return Camera(
        id=row.id,
        establishment_id=row.establishment_id,
        name=row.name,
        encrypted_url=row.encrypted_url,
        enabled=row.enabled,
    )


class SqlCameraRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def add(self, camera: Camera) -> None:
        async with self._sessions.begin() as session:
            session.add(
                CameraRow(
                    id=camera.id,
                    establishment_id=camera.establishment_id,
                    name=camera.name,
                    encrypted_url=camera.encrypted_url,
                    enabled=camera.enabled,
                )
            )

    async def save(self, camera: Camera) -> None:
        async with self._sessions.begin() as session:
            row = await session.get(CameraRow, camera.id)
            if row is not None:
                row.name = camera.name
                row.enabled = camera.enabled

    async def get(self, camera_id: UUID) -> Camera | None:
        async with self._sessions() as session:
            row = await session.get(CameraRow, camera_id)
            return _to_model(row) if row else None

    async def delete(self, camera_id: UUID) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(CameraRow).where(CameraRow.id == camera_id))

    async def list_for(self, establishment_id: UUID) -> list[Camera]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(CameraRow)
                .where(CameraRow.establishment_id == establishment_id)
                .order_by(CameraRow.name)
            )
            return [_to_model(row) for row in rows]

    async def list_enabled(self) -> list[Camera]:
        async with self._sessions() as session:
            rows = await session.scalars(select(CameraRow).where(CameraRow.enabled))
            return [_to_model(row) for row in rows]

    async def list_all(self) -> list[Camera]:
        async with self._sessions() as session:
            return [_to_model(row) for row in await session.scalars(select(CameraRow))]


class SqlImouOwners:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def owner_of(self, device_id: str) -> UUID | None:
        async with self._sessions() as session:
            row = await session.get(ImouDeviceRow, device_id)
            return row.establishment_id if row else None

    async def claim(self, device_id: str, establishment_id: UUID) -> None:
        """Adjudica la cámara al local. Si ya es de otro, ConflictError."""
        try:
            async with self._sessions.begin() as session:
                row = await session.get(ImouDeviceRow, device_id)
                if row is None:
                    session.add(
                        ImouDeviceRow(
                            device_id=device_id,
                            establishment_id=establishment_id,
                            created_at=datetime.now(UTC),
                        )
                    )
                elif row.establishment_id != establishment_id:
                    raise ConflictError("Esa cámara ya está registrada en otro local")
        except IntegrityError as error:
            # Otro local la adjudicó al mismo tiempo.
            if await self.owner_of(device_id) != establishment_id:
                raise ConflictError("Esa cámara ya está registrada en otro local") from error

    async def owned_by(self, establishment_id: UUID) -> set[str]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(ImouDeviceRow.device_id).where(
                    ImouDeviceRow.establishment_id == establishment_id
                )
            )
            return set(rows)
