"""Cliente mínimo de Supabase Storage: archivos compartidos por todos los backends.

Con el backend en la nube y otro en el local sobre la misma base, el disco de cada uno no sirve:
lo que guarda uno, el otro no lo ve, y el disco de la nube se borra en cada despliegue.
El bucket es privado y se usa con la clave de servicio: los archivos solo salen a través del
backend, que aplica sus permisos.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

import httpx

_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
_PAGE = 1000


@dataclass(frozen=True, slots=True)
class StoredObject:
    name: str
    created_at: datetime


class SupabaseStorage:
    def __init__(
        self,
        url: str,
        service_key: str,
        bucket: str,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._base = f"{url.rstrip('/')}/storage/v1/object"
        self._bucket = bucket
        self._headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=_TIMEOUT))

    def _url(self, path: str) -> str:
        return f"{self._base}/{self._bucket}/{quote(path, safe='/')}"

    async def upload(self, path: str, data: bytes, content_type: str) -> None:
        async with self._client_factory() as client:
            response = await client.post(
                self._url(path),
                content=data,
                headers={**self._headers, "Content-Type": content_type, "x-upsert": "true"},
            )
            response.raise_for_status()

    async def download(self, path: str) -> bytes | None:
        async with self._client_factory() as client:
            response = await client.get(self._url(path), headers=self._headers)
        # Storage responde 400 o 404 cuando el archivo no existe.
        if response.status_code in (400, 404):
            return None
        response.raise_for_status()
        return response.content

    async def delete(self, paths: list[str]) -> None:
        if not paths:
            return
        async with self._client_factory() as client:
            response = await client.request(
                "DELETE",
                f"{self._base}/{self._bucket}",
                json={"prefixes": paths},
                headers=self._headers,
            )
            response.raise_for_status()

    async def list(self, prefix: str) -> list[StoredObject]:
        """Archivos de una carpeta, de a páginas. `prefix` es la carpeta, sin barra final."""
        found: list[StoredObject] = []
        offset = 0
        async with self._client_factory() as client:
            while True:
                response = await client.post(
                    f"{self._base}/list/{self._bucket}",
                    json={"prefix": prefix, "limit": _PAGE, "offset": offset},
                    headers=self._headers,
                )
                response.raise_for_status()
                page = response.json()
                for item in page:
                    if item.get("id") and item.get("created_at"):
                        created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                        found.append(StoredObject(f"{prefix}/{item['name']}", created))
                if len(page) < _PAGE:
                    return found
                offset += _PAGE
