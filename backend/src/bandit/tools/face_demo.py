"""Demostración educativa y aislada: ¿la persona de una foto es la misma de las fotos de referencia?

Solo compara fotos que el propio usuario pone en dos carpetas locales, con su consentimiento:

    referencia/   fotos de la persona que se quiere reconocer
    prueba/       fotos para comprobar si esa persona aparece

No usa el directorio de la Policía, no guarda nada en la base de datos, no crea incidentes,
no aparece en el Panel y no envía mensajes. La "alerta" se imprime solo en esta consola.

Uso, dentro del contenedor del backend:

    python -m bandit.tools.face_demo /app/var/rostros
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_MAX_REFERENCES = 3
MATCH_THRESHOLD = 0.8

INSTRUCTION = """\
Eres una prueba educativa de verificación facial con consentimiento de la persona.
Las primeras imágenes son fotos de referencia de UNA misma persona. La última es la foto de prueba.
Indica si en la foto de prueba aparece esa misma persona. No digas nombres ni datos personales:
solo compara rasgos visibles. Si la cara no se ve bien, dilo y usa una confianza baja.
"""


class _Verdict(BaseModel):
    same_person: bool
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(max_length=240)


@dataclass(frozen=True, slots=True)
class Comparison:
    name: str
    same_person: bool
    confidence: float
    explanation: str

    @property
    def alert(self) -> bool:
        return self.same_person and self.confidence >= MATCH_THRESHOLD


class FaceComparer(Protocol):
    async def compare(self, references: list[bytes], probe: bytes) -> _Verdict: ...


class GeminiFaceComparer:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai
        from google.genai import types

        from bandit.shared.gemini import http_options

        self._types = types
        self._client = genai.Client(api_key=api_key, http_options=http_options(3, 10))
        self._model = model
        self._config = types.GenerateContentConfig(
            system_instruction=INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_Verdict,
        )

    async def compare(self, references: list[bytes], probe: bytes) -> _Verdict:
        types = self._types
        parts = [types.Part.from_bytes(data=image, mime_type="image/jpeg") for image in references]
        parts.append(types.Part.from_text(text="Foto de prueba:"))
        parts.append(types.Part.from_bytes(data=probe, mime_type="image/jpeg"))
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=types.Content(role="user", parts=parts),
            config=self._config,
        )
        parsed = response.parsed
        if isinstance(parsed, _Verdict):
            return parsed
        return _Verdict.model_validate_json(response.text or "")


def load_images(folder: Path) -> list[tuple[str, bytes]]:
    if not folder.is_dir():
        return []
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in _EXTENSIONS)
    return [(path.name, path.read_bytes()) for path in files]


async def run_demo(
    references: list[bytes], probes: list[tuple[str, bytes]], comparer: FaceComparer
) -> list[Comparison]:
    results: list[Comparison] = []
    for name, probe in probes:
        try:
            verdict = await comparer.compare(references[:_MAX_REFERENCES], probe)
        except Exception as error:
            results.append(
                Comparison(name, False, 0.0, f"No se pudo comparar: {type(error).__name__}")
            )
            continue
        results.append(
            Comparison(name, verdict.same_person, verdict.confidence, verdict.explanation)
        )
    return results


async def _main(root: Path) -> int:
    from bandit.shared.config import get_settings

    settings = get_settings()
    if not settings.gemini_api_key:
        print("Falta GEMINI_API_KEY.")
        return 1
    references = [image for _, image in load_images(root / "referencia")]
    probes = load_images(root / "prueba")
    if not references or not probes:
        print(f"Pon fotos en {root / 'referencia'} y en {root / 'prueba'}.")
        return 1
    model = settings.gemini_directory_model or settings.gemini_model
    print(f"Demostración educativa con {model}. Nada se guarda ni se envía.\n")
    results = await run_demo(references, probes, GeminiFaceComparer(settings.gemini_api_key, model))
    for result in results:
        verdict = "COINCIDE" if result.same_person else "no coincide"
        print(f"{result.name}: {verdict} ({result.confidence:.0%}) · {result.explanation}")
        if result.alert:
            print("   >>> ALERTA DE PRUEBA (solo en consola): la persona de referencia aparece.")
    alerts = sum(result.alert for result in results)
    print(f"\n{alerts} de {len(results)} fotos de prueba generarían alerta.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="Carpeta con referencia/ y prueba/")
    sys.exit(asyncio.run(_main(parser.parse_args().root)))


if __name__ == "__main__":
    main()
