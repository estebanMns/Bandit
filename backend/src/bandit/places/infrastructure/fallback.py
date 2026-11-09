"""Usa la primera fuente de CAI que responda."""

import logging
from collections.abc import Sequence

from bandit.places.domain.models import Place
from bandit.places.domain.ports import PoliceStations
from bandit.shared.error_summary import describe_error
from bandit.shared.errors import UnavailableError

logger = logging.getLogger(__name__)


class FirstAvailableStations:
    def __init__(self, sources: Sequence[PoliceStations]) -> None:
        self._sources = sources

    async def around(self, latitude: float, longitude: float, radius_m: int) -> list[Place]:
        for source in self._sources:
            try:
                return await source.around(latitude, longitude, radius_m)
            except Exception as error:
                logger.warning("%s no respondió: %s", type(source).__name__, describe_error(error))
        raise UnavailableError(
            "El servicio de mapas no respondió. Intenta de nuevo en unos minutos."
        )
