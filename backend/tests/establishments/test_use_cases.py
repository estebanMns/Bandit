from uuid import uuid4

import pytest

from bandit.establishments.domain.models import WhatsAppNumber
from bandit.establishments.module import EstablishmentsModule
from bandit.shared.errors import InvalidDataError, NotFoundError


@pytest.fixture
def module(sessions) -> EstablishmentsModule:
    return EstablishmentsModule(sessions)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+573001234567", "+573001234567"),
        ("+57 300 123 4567", "+573001234567"),
        ("+57 (300) 123-4567", "+573001234567"),
    ],
)
def test_whatsapp_number_normalizes_separators(raw, expected):
    assert WhatsAppNumber.parse(raw).value == expected


@pytest.mark.parametrize("raw", ["3001234567", "+0123456789", "+57", "+57abc4567890", ""])
def test_whatsapp_number_rejects_invalid_values(raw):
    with pytest.raises(InvalidDataError):
        WhatsAppNumber.parse(raw)


async def test_registers_and_clears_the_cai_number(module):
    establishment = await module.create.execute("Bar La Esquina", "Calle 10 # 5-20")

    await module.set_cai_whatsapp.execute(establishment.id, "+57 300 123 4567")
    saved = await module.get.execute(establishment.id)
    assert saved.cai_whatsapp == WhatsAppNumber("+573001234567")

    await module.set_cai_whatsapp.execute(establishment.id, None)
    assert (await module.get.execute(establishment.id)).cai_whatsapp is None


async def test_invalid_cai_number_is_not_saved(module):
    establishment = await module.create.execute("Bar La Esquina", "Calle 10 # 5-20")

    with pytest.raises(InvalidDataError):
        await module.set_cai_whatsapp.execute(establishment.id, "123")

    assert (await module.get.execute(establishment.id)).cai_whatsapp is None


async def test_unknown_establishment_is_reported(module):
    with pytest.raises(NotFoundError):
        await module.get.execute(uuid4())


async def test_blank_name_is_rejected(module):
    with pytest.raises(InvalidDataError):
        await module.create.execute("   ", "Calle 10")
