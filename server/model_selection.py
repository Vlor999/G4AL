"""The model the next command goes to, chosen by the player among the available ones.

Entry point state, not a game rule: which LLM interprets an order does not change what
the order does.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from api.model_catalog import CatalogModel, LlmProvider
from game.npc import NPC
from game.ports import TextOrderInterpreter, VoiceOrderInterpreter


@dataclass(frozen=True)
class OrderInterpreters:
    """The adapters of one provider. ``voice`` is ``None`` when the provider has no
    speech input: the game then takes typed commands only."""

    text: TextOrderInterpreter
    voice: VoiceOrderInterpreter | None
    register_roster: Callable[[Sequence[NPC]], None]


@dataclass(frozen=True)
class SelectedModel:
    """A model with the interpreters that reach it. ``voice`` is ``None`` when the
    model does not hear audio: push-to-talk is then off."""

    model: CatalogModel
    text: TextOrderInterpreter
    voice: VoiceOrderInterpreter | None


class ModelSelection:
    """The selected model among ``available_models``; safe to use from any thread.

    ``interpreters`` holds the adapters of every provider an available model belongs to.
    Raises ``ValueError`` when ``selected`` is not available.
    """

    def __init__(
        self,
        *,
        available_models: Sequence[CatalogModel],
        selected: CatalogModel,
        interpreters: Mapping[LlmProvider, OrderInterpreters],
    ) -> None:
        if selected not in available_models:
            raise ValueError(f"{selected.model_id} is not an available model")
        self.available_models = tuple(available_models)
        self._interpreters = dict(interpreters)
        self._selected = selected
        self._lock = threading.Lock()

    def select(self, model_id: str) -> bool:
        """Make ``model_id`` the model of the next commands; returns False, changing
        nothing, when no available model has this id."""
        model = next((m for m in self.available_models if m.model_id == model_id), None)
        if model is None:
            return False
        with self._lock:
            self._selected = model
        return True

    def selected(self) -> SelectedModel:
        with self._lock:
            model = self._selected
        interpreters = self._interpreters[model.provider]
        return SelectedModel(
            model=model,
            text=interpreters.text,
            voice=interpreters.voice if model.has_voice_input else None,
        )
