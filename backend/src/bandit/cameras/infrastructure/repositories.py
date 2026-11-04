"""Repositorio SQL de cámaras."""

from uuid import UUID

from sqlalchemy import delete, select

from bandit.cameras.domain.models import Camera
from bandit.cameras.infrastructure.tables import CameraRow
from bandit.shared.db import SessionFactory


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
