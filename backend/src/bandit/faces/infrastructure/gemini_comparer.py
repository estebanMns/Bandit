"""Comparación de rostros con Gemini y salida estructurada."""

from collections.abc import Sequence

from pydantic import BaseModel, Field

from bandit.faces.domain.models import FaceVerdict

INSTRUCTION = """\
Prueba de verificación facial con consentimiento de la persona de referencia.
Las primeras imágenes son fotos de referencia de UNA misma persona. La última es una imagen
de una cámara de seguridad. Primero indica si en la imagen de la cámara se ve la cara de
alguien. Luego indica si esa cara es la de la persona de referencia.
Sé estricto: parecerse no basta. Si dudas, responde que no es la misma persona.
No digas nombres ni datos personales: solo compara rasgos visibles.
Escribe la explicación en español, en una o dos frases.
"""


class _Verdict(BaseModel):
    face_visible: bool
    same_person: bool
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(max_length=240)


class GeminiFaceComparer:
    def __init__(self, api_key: str, models: Sequence[str]) -> None:
        from google import genai
        from google.genai import types

        from bandit.shared.gemini import ModelChain, http_options

        self._chain = ModelChain(models)
        self._types = types
        self._client = genai.Client(api_key=api_key, http_options=http_options(2, 10))
        self._config = types.GenerateContentConfig(
            system_instruction=INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_Verdict,
        )

    @property
    def model(self) -> str:
        """El modelo en uso: pasa al siguiente mientras uno no tenga cuota."""
        return self._chain.active

    async def compare(self, references: Sequence[bytes], probe: bytes) -> FaceVerdict:
        return await self._chain.run(lambda model: self._compare(model, references, probe))

    async def _compare(self, model: str, references: Sequence[bytes], probe: bytes) -> FaceVerdict:
        types = self._types
        parts = [types.Part.from_bytes(data=image, mime_type="image/jpeg") for image in references]
        parts.append(types.Part.from_text(text="Imagen de la cámara:"))
        parts.append(types.Part.from_bytes(data=probe, mime_type="image/jpeg"))
        response = await self._client.aio.models.generate_content(
            model=model,
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
