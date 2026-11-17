"""Comparación de rostros con Gemini y salida estructurada."""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from bandit.faces.domain.models import FaceVerdict, WatchedPerson

if TYPE_CHECKING:
    from google.genai import types as genai

INSTRUCTION = """\
Prueba de verificación facial con consentimiento de la persona de referencia.
Las primeras imágenes son fotos de referencia de UNA misma persona. La última es una imagen
de una cámara de seguridad. Primero indica si en la imagen de la cámara se ve la cara de
alguien. Luego indica si esa cara es la de la persona de referencia.
Sé estricto: parecerse no basta. Si dudas, responde que no es la misma persona.
No digas nombres ni datos personales: solo compara rasgos visibles.
Escribe la explicación en español, en una o dos frases.
"""


IDENTIFY_INSTRUCTION = """\
Búsqueda facial con consentimiento y revisión humana posterior.
Recibirás fotos de referencia, cada una precedida por su número de candidato ("Candidato 0",
"Candidato 1", ...), y al final una imagen de una cámara de seguridad.
Primero indica si en la imagen de la cámara se ve la cara de alguien. Luego indica si esa cara
corresponde a UNO de los candidatos; si ninguno coincide, usa candidate = -1.
Sé estricto: parecerse no basta. Si dudas, usa candidate = -1.
No digas nombres ni datos personales: solo compara rasgos visibles.
Escribe la explicación en español, en una o dos frases.
"""


class _Verdict(BaseModel):
    face_visible: bool
    same_person: bool
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(max_length=240)


class _Identification(BaseModel):
    face_visible: bool
    candidate: int = Field(ge=-1)
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(max_length=240)


def _mime(image: bytes) -> str:
    return "image/png" if image.startswith(b"\x89PNG") else "image/jpeg"


class GeminiFaceComparer:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai
        from google.genai import types

        from bandit.shared.gemini import http_options

        self.model = model
        self._types = types
        self._client = genai.Client(api_key=api_key, http_options=http_options(2, 10))
        self._config = types.GenerateContentConfig(
            system_instruction=INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_Verdict,
        )
        self._identify_config = types.GenerateContentConfig(
            system_instruction=IDENTIFY_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_Identification,
        )

    async def compare(self, references: Sequence[bytes], probe: bytes) -> FaceVerdict:
        types = self._types
        parts = [types.Part.from_bytes(data=image, mime_type="image/jpeg") for image in references]
        parts.append(types.Part.from_text(text="Imagen de la cámara:"))
        parts.append(types.Part.from_bytes(data=probe, mime_type="image/jpeg"))
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=types.Content(role="user", parts=parts),
            config=self._config,
        )
        parsed = response.parsed
        verdict = (
            parsed
            if isinstance(parsed, _Verdict)
            else _Verdict.model_validate_json(response.text or "")
        )
        return FaceVerdict(
            verdict.face_visible, verdict.same_person, verdict.confidence, verdict.explanation
        )

    async def identify(
        self, candidates: Sequence[WatchedPerson], probe: bytes
    ) -> tuple[FaceVerdict, int | None]:
        types = self._types
        parts: list[genai.Part] = []
        for number, person in enumerate(candidates):
            # Solo el número viaja con la foto: los nombres no salen de Bandit.
            parts.append(types.Part.from_text(text=f"Candidato {number}:"))
            parts.append(
                types.Part.from_bytes(
                    data=person.references[0], mime_type=_mime(person.references[0])
                )
            )
        parts.append(types.Part.from_text(text="Imagen de la cámara:"))
        parts.append(types.Part.from_bytes(data=probe, mime_type="image/jpeg"))
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=types.Content(role="user", parts=parts),
            config=self._identify_config,
        )
        parsed = response.parsed
        result = (
            parsed
            if isinstance(parsed, _Identification)
            else _Identification.model_validate_json(response.text or "")
        )
        chosen = result.candidate if 0 <= result.candidate < len(candidates) else None
        verdict = FaceVerdict(
            result.face_visible, chosen is not None, result.confidence, result.explanation
        )
        return verdict, chosen
