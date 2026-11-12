"""Prueba local: pone a una persona (con su consentimiento) en el directorio y la busca con IA.

Solo para este equipo de pruebas. Pasos:

    agregar   pone a la persona como registro de prueba en el directorio, arriba de todos
    probar    compara su cara con fotos o con una cámara en vivo; si coincide, crea la alerta
              "Persona buscada identificada" en Eventos, pendiente de revisión
    quitar    retira el registro de prueba del directorio

Las fotos de referencia salen de <carpeta>/referencia y las de prueba de <carpeta>/prueba.
La alerta queda "Por revisar": como cualquier incidente, nada sale de Bandit sin que un
operador la confirme.

Uso, dentro del contenedor del backend:

    python -m bandit.tools.wanted_match agregar --nombre "Nombre" --fotos /app/var/rostros
    python -m bandit.tools.wanted_match probar --nombre "Nombre" --fotos /app/var/rostros \\
        --local "donpancho" [--camara "camara principal" --minutos 3]
    python -m bandit.tools.wanted_match quitar --nombre "Nombre"
"""

import argparse
import asyncio
import sys
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from bandit.tools.face_demo import FaceComparer, load_images
from bandit.tools.simulate_alert import TEST_CAMERA_NAME, photo_camera_id

INCIDENT_TYPE = "wanted_match"
MATCH_THRESHOLD = 0.8
TEST_CRIME = "Homicidio, secuestro y terrorismo (registro de prueba local)"
TEST_REWARD = "HASTA 10.000 SMLMV"
TEST_ALIAS = "Registro de prueba"
_MAX_REFERENCES = 3
_DESCRIPTION_LIMIT = 300
_PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True, slots=True)
class MatchReport:
    name: str
    same_person: bool
    confidence: float
    explanation: str
    alerted: bool


def describe_match(person: str, confidence: float, explanation: str) -> str:
    text = (
        f"Coincidencia con {person}, de la lista de buscados (registro de prueba), "
        f"{confidence:.0%}: {explanation}"
    )
    return text[:_DESCRIPTION_LIMIT]


async def watch(
    probes: AsyncIterator[tuple[str, bytes]],
    references: list[bytes],
    comparer: FaceComparer,
    on_match: Callable[[str, bytes, float, str], Awaitable[object]],
) -> list[MatchReport]:
    """Compara cada imagen; la primera coincidencia segura crea una sola alerta."""
    reports: list[MatchReport] = []
    alerted = False
    async for name, jpeg in probes:
        try:
            verdict = await comparer.compare(references[:_MAX_REFERENCES], jpeg)
        except Exception as error:
            reports.append(MatchReport(name, False, 0.0, f"No se pudo comparar: {error}", False))
            continue
        match = verdict.same_person and verdict.confidence >= MATCH_THRESHOLD
        alert_now = match and not alerted
        if alert_now:
            await on_match(name, jpeg, verdict.confidence, verdict.explanation)
            alerted = True
        reports.append(
            MatchReport(
                name, verdict.same_person, verdict.confidence, verdict.explanation, alert_now
            )
        )
    return reports


async def _from_photos(photos: list[tuple[str, bytes]]) -> AsyncIterator[tuple[str, bytes]]:
    for item in photos:
        yield item


async def _from_stream(
    frames: AsyncIterator[bytes], every_seconds: float, minutes: float
) -> AsyncIterator[tuple[str, bytes]]:
    deadline = time.monotonic() + minutes * 60
    next_at = 0.0
    async for jpeg in frames:
        now = time.monotonic()
        if now >= deadline:
            return
        if now >= next_at:
            next_at = now + every_seconds
            yield datetime.now(UTC).astimezone().strftime("cámara %H:%M:%S"), jpeg


async def _add(name: str, root: Path) -> int:
    from bandit.bootstrap import build_application
    from bandit.shared.config import get_settings

    folder = root / "referencia"
    photos = (
        sorted(p for p in folder.iterdir() if p.suffix.lower() in _PHOTO_SUFFIXES)
        if folder.is_dir()
        else []
    )
    if not photos:
        print(f"Pon fotos en {root / 'referencia'}.")
        return 1
    app = build_application(get_settings())
    try:
        record = await app.directory.local_tests.add(
            name,
            TEST_ALIAS,
            TEST_CRIME,
            TEST_REWARD,
            "Nariño",
            photos[0].read_bytes(),
            photos[0].suffix,
        )
    finally:
        await app.engine.dispose()
    print(f"'{record.name}' quedó primero en el directorio: {record.reward} · {record.crime}.")
    print("Revisa la página Directorio (puede tardar unos segundos en actualizarse).")
    return 0


async def _remove(name: str) -> int:
    from bandit.bootstrap import build_application
    from bandit.shared.config import get_settings

    app = build_application(get_settings())
    try:
        removed = await app.directory.local_tests.remove(name)
    finally:
        await app.engine.dispose()
    print(
        "Registro de prueba retirado."
        if removed
        else "No hay un registro de prueba con ese nombre."
    )
    return 0


async def _probe(
    name: str, root: Path, local_name: str, camera_name: str | None, minutes: float, every: float
) -> int:
    from bandit.bootstrap import build_application
    from bandit.directory.domain.models import slugify
    from bandit.incidents.domain.models import Incident
    from bandit.shared.config import get_settings
    from bandit.shared.errors import NotFoundError
    from bandit.tools.face_demo import GeminiFaceComparer

    settings = get_settings()
    if not settings.gemini_api_key:
        print("Falta GEMINI_API_KEY.")
        return 1
    references = [image for _, image in load_images(root / "referencia")]
    if not references:
        print(f"Pon fotos en {root / 'referencia'}.")
        return 1
    app = build_application(settings)
    try:
        try:
            record = await app.directory.get.execute(slugify(name))
        except NotFoundError:
            record = None
        if record is None or not record.local_test:
            print("Primero agrega a la persona con: agregar --nombre ...")
            return 1
        locals_ = await app.establishments.list_all.execute()
        match = [item for item in locals_ if item.name.lower() == local_name.lower()]
        if not match:
            print("No existe ese local. Locales:", ", ".join(item.name for item in locals_))
            return 1
        establishment = match[0]

        if camera_name:
            cameras = await app.cameras.list_for.execute(establishment.id)
            chosen = [c for c in cameras if c.name.lower() == camera_name.lower()]
            if not chosen:
                print("No existe esa cámara. Cámaras:", ", ".join(c.name for c in cameras))
                return 1
            camera_id, shown_name = chosen[0].id, chosen[0].name
            probes = _from_stream(_camera_frames(settings, chosen[0].encrypted_url), every, minutes)
            print(f"Mirando '{shown_name}' durante {minutes:g} min, una imagen cada {every:g} s…")
        else:
            photos = load_images(root / "prueba")
            if not photos:
                print(f"Pon fotos en {root / 'prueba'} o usa --camara.")
                return 1
            camera_id, shown_name = photo_camera_id(establishment.id), TEST_CAMERA_NAME
            probes = _from_photos(photos)

        created: list[UUID] = []

        async def on_match(_: str, jpeg: bytes, confidence: float, explanation: str) -> object:
            incident = Incident(
                id=uuid4(),
                establishment_id=establishment.id,
                camera_id=camera_id,
                camera_name=shown_name,
                type=INCIDENT_TYPE,
                severity="high",
                confidence=confidence,
                description=describe_match(record.name, confidence, explanation),
                detected_at=datetime.now(UTC),
            )
            created.append(incident.id)
            return await app.incidents.record_situation.record(incident, jpeg)

        model = settings.gemini_directory_model or settings.gemini_model
        print(f"Comparando con {model}.\n")
        reports = await watch(
            probes, references, GeminiFaceComparer(settings.gemini_api_key, model), on_match
        )
    finally:
        await app.engine.dispose()

    for report in reports:
        verdict = "COINCIDE" if report.same_person else "no coincide"
        mark = "  <- ALERTA creada en Eventos" if report.alerted else ""
        print(f"{report.name}: {verdict} ({report.confidence:.0%}) · {report.explanation}{mark}")
    if created:
        print(f"\nAlerta 'Persona buscada identificada' creada en '{establishment.name}'.")
        print("Ábrela en Eventos (recarga la página si ya la tenías abierta).")
    else:
        print("\nNo hubo coincidencia segura: no se creó ninguna alerta.")
    return 0


async def _camera_frames(settings: object, encrypted_url: str) -> AsyncIterator[bytes]:
    from bandit.cameras.infrastructure.fernet_cipher import FernetUrlCipher
    from bandit.cameras.infrastructure.ffmpeg_source import FfmpegFrameSource
    from bandit.cameras.infrastructure.imou_cloud import ImouCloudResolver
    from bandit.cameras.infrastructure.resolving_source import ResolvingFrameSource
    from bandit.shared.config import Settings

    assert isinstance(settings, Settings)
    url = FernetUrlCipher(settings.camera_encryption_key).decrypt(encrypted_url)
    source = ResolvingFrameSource(
        FfmpegFrameSource(settings.ffmpeg_path, settings.video_fps, settings.video_width),
        ImouCloudResolver(settings.imou_app_id, settings.imou_app_secret, settings.imou_api_url),
    )
    async for jpeg in source.stream(url):
        yield jpeg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    steps = parser.add_subparsers(dest="step", required=True)
    add = steps.add_parser("agregar")
    add.add_argument("--nombre", required=True)
    add.add_argument("--fotos", type=Path, required=True)
    probe = steps.add_parser("probar")
    probe.add_argument("--nombre", required=True)
    probe.add_argument("--fotos", type=Path, required=True)
    probe.add_argument("--local", required=True)
    probe.add_argument("--camara")
    probe.add_argument("--minutos", type=float, default=3)
    probe.add_argument("--cada", type=float, default=5, help="Segundos entre imágenes")
    remove = steps.add_parser("quitar")
    remove.add_argument("--nombre", required=True)
    args = parser.parse_args()
    if args.step == "agregar":
        code = asyncio.run(_add(args.nombre, args.fotos))
    elif args.step == "probar":
        code = asyncio.run(
            _probe(args.nombre, args.fotos, args.local, args.camara, args.minutos, args.cada)
        )
    else:
        code = asyncio.run(_remove(args.nombre))
    sys.exit(code)


if __name__ == "__main__":
    main()
