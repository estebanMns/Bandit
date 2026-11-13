"""La cadena de modelos: el que se queda sin cuota descansa y se usa el siguiente."""

import pytest
from google.genai import errors

from bandit.shared.gemini import ModelChain, model_list


def quota() -> errors.ClientError:
    return errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}})


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_model_list_joins_in_order_without_blanks_or_repeats():
    assert model_list("a", "", "b, a ,c", "c") == ["a", "b", "c"]


async def test_an_exhausted_model_rests_and_comes_back_later():
    clock = Clock()
    chain = ModelChain(["a", "b"], rest_seconds=60, clock=clock)
    used: list[str] = []

    async def call(model: str) -> str:
        used.append(model)
        if model == "a" and clock.now < 60:
            raise quota()
        return model

    assert await chain.run(call) == "b"
    assert await chain.run(call) == "b"
    clock.now = 61
    assert await chain.run(call) == "a"
    assert used == ["a", "b", "b", "a"]


async def test_other_errors_are_not_treated_as_quota():
    chain = ModelChain(["a", "b"])

    async def call(model: str) -> str:
        raise errors.ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT"}})

    with pytest.raises(errors.ClientError):
        await chain.run(call)
    assert chain.active == "a"
