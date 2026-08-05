"""Proposal-generation boundary for deterministic and OpenAI planners."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable

from src.agent.live_planner import LiveProposal


@runtime_checkable
class Planner(Protocol):
    def curated(self, question: str) -> tuple[Any, str] | None: ...

    def live(
        self,
        question: str,
        api_key: str,
        model: str,
        conversation_context: list[dict[str, Any]] | None,
    ) -> LiveProposal: ...


class ExistingPlanner:
    """Adapter retaining the existing curated lookup and structured live planner."""

    def __init__(
        self,
        db_path: Path,
        curated_lookup: Callable[[str], tuple[Any, str] | None],
        live_generator: Callable[..., LiveProposal],
    ):
        self.db_path = Path(db_path)
        self._curated_lookup = curated_lookup
        self._live_generator = live_generator

    def curated(self, question: str) -> tuple[Any, str] | None:
        return self._curated_lookup(question)

    def live(self, question, api_key, model, conversation_context):
        # The legacy generator discovers and bounds catalog metadata itself; it
        # never receives a connection or execution capability.
        return self._live_generator(question, api_key, self.db_path, model, conversation_context)
