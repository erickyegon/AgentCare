"""LLM provider abstraction.

The agents depend on a small, uniform interface — ``structured()`` — which returns a
validated Pydantic object. Two providers implement it:

* ``AnthropicLLM``  — real Claude via LangChain structured output, with retry/backoff.
* ``MockLLM``       — deterministic, input-driven decisions so the whole system runs
  offline / in CI with no API key. The mock is genuine logic over the input (not a fixed
  response); it exists so tests and demos never hard-fail on a missing key.

If the real provider errors after all retries, it degrades to the supplied mock closure so a
run never dies mid-flight — the fallback is recorded in the agent trace for transparency.
"""

from __future__ import annotations

import logging
from typing import Callable, TypeVar

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger("agentcare.llm")

T = TypeVar("T", bound=BaseModel)


class BaseLLM:
    provider = "base"

    def structured(
        self, *, system: str, user: str, schema: type[T], mock: Callable[[], T]
    ) -> tuple[T, str]:
        raise NotImplementedError


class MockLLM(BaseLLM):
    """Deterministic provider — evaluates the mock closure built from the request."""

    provider = "mock"

    def structured(
        self, *, system: str, user: str, schema: type[T], mock: Callable[[], T]
    ) -> tuple[T, str]:
        return mock(), self.provider


class AnthropicLLM(BaseLLM):
    """Real Claude provider using LangChain's structured-output binding."""

    provider = "anthropic"

    def __init__(self) -> None:
        # Imported lazily so the mock path has no hard dependency on the SDK being importable.
        from langchain_anthropic import ChatAnthropic

        self._model = ChatAnthropic(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.anthropic_api_key,
            timeout=30,
            max_retries=0,  # we manage retries with tenacity below
        )

    def structured(
        self, *, system: str, user: str, schema: type[T], mock: Callable[[], T]
    ) -> tuple[T, str]:
        from langchain_core.messages import HumanMessage, SystemMessage

        structured_model = self._model.with_structured_output(schema)

        @retry(
            stop=stop_after_attempt(max(1, settings.llm_max_retries)),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=6),
            reraise=True,
        )
        def _call() -> T:
            return structured_model.invoke(
                [SystemMessage(content=system), HumanMessage(content=user)]
            )

        try:
            return _call(), self.provider
        except Exception as exc:  # pragma: no cover - network/provider failure path
            logger.warning("Anthropic call failed (%s); falling back to deterministic mock.", exc)
            return mock(), "mock-fallback"


def get_llm() -> BaseLLM:
    """Return the configured provider, or the mock when no real LLM is usable."""
    if settings.use_real_llm:
        try:
            return AnthropicLLM()
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not initialize Anthropic (%s); using mock provider.", exc)
    return MockLLM()
