"""Extrae el texto del volante en local: las fotos del PDF nunca salen del servidor."""

import io

from pypdf import PdfReader
from pypdf.errors import PyPdfError


def read_pdf_text(pdf: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except PyPdfError:
        return ""
