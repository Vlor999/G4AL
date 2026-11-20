"""Mistral adapter of the ``TextOrderInterpreter`` and ``VoiceOrderInterpreter`` ports.

Each command goes to the catalog model the caller names: a typed one as text, a
recorded one as audio to a voice model (Voxtral) in one multimodal call, with no
transcription step. Both calls send the shared system prompt and are constrained the
same way: the model must call the ``give_npc_orders`` function (``tool_choice="any"``)
once (``parallel_tool_calls=False``), whose parameters are ``ORDERS_SCHEMA``. The arguments
of every such call are validated by ``parse_orders``; an answer that breaks the
contract becomes a ``CommandRefused`` outcome.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from functools import partial

from loguru import logger
from mistralai.client import Mistral
from mistralai.client.models import (
    ChatCompletionRequestMessageTypedDict,
    ChatCompletionResponse,
    ToolTypedDict,
)

from api.constants import ORDERS_TOOL_NAME
from api.logger import PipelineLogger
from api.order_contract import (
    ORDERS_SCHEMA,
    Roster,
    RosterEntry,
    build_orders_for_log,
    build_roster,
    build_system_prompt,
    parse_orders,
)
from game.npc import NPC
from game.orders import CommandRefused, NpcOrder, RefusalReason
from game.ports import OrderInterpretationError

ORDERS_TOOL: ToolTypedDict = {
    "type": "function",
    "function": {
        "name": ORDERS_TOOL_NAME,
        "description": "Give the NPCs the orders of the player's command.",
        "parameters": ORDERS_SCHEMA,
    },
}

VOICE_INSTRUCTION = "Give the orders spoken in this voice command."
TEXT_INSTRUCTION = "Give the orders of this typed command:"


def _build_voice_messages(
    audio: bytes, roster: Roster
) -> list[ChatCompletionRequestMessageTypedDict]:
    audio_b64 = base64.b64encode(audio).decode("utf-8")
    return [
        {"role": "system", "content": build_system_prompt(roster)},
        {
            "role": "user",
            "content": [
                {"type": "input_audio", "input_audio": audio_b64},
                {"type": "text", "text": VOICE_INSTRUCTION},
            ],
        },
    ]


def _build_text_messages(
    command: str, roster: Roster
) -> list[ChatCompletionRequestMessageTypedDict]:
    return [
        {"role": "system", "content": build_system_prompt(roster)},
        {"role": "user", "content": f"{TEXT_INSTRUCTION}\n{command}"},
    ]


def read_orders_answer(
    response: ChatCompletionResponse, roster: Roster
) -> list[NpcOrder] | CommandRefused:
    """The orders of every ``give_npc_orders`` call in the answer, in call order, or
    why the answer is refused.

    The request asks for a single call, but an answer that still holds several loses
    none of them: their orders are merged, and one refused call refuses the answer.
    A choice without a message gives no orders.
    """
    message = response.choices[0].message
    tool_calls = (message.tool_calls if message is not None else None) or []
    orders_calls = [call for call in tool_calls if call.function.name == ORDERS_TOOL_NAME]
    if not orders_calls:
        return CommandRefused(RefusalReason.NO_ORDERS_GIVEN)
    orders: list[NpcOrder] = []
    for tool_call in orders_calls:
        call_orders = parse_orders(tool_call.function.arguments, roster)
        if isinstance(call_orders, CommandRefused):
            return call_orders
        orders.extend(call_orders)
    return orders


class MistralOrderInterpreter:
    """Both order interpreter ports, backed by one Mistral call per command.

    The NPC roster the prompt lists comes from ``register_roster``. Every call is
    logged, with its cost, through ``pipeline_logger``.
    """

    def __init__(self, client: Mistral, *, pipeline_logger: PipelineLogger) -> None:
        self._client = client
        self._pipeline_logger = pipeline_logger
        self._roster: dict[int, RosterEntry] = {}

    @classmethod
    def from_api_key(
        cls, api_key: str, *, pipeline_logger: PipelineLogger
    ) -> MistralOrderInterpreter:
        return cls(Mistral(api_key=api_key), pipeline_logger=pipeline_logger)

    def register_roster(self, npcs: Sequence[NPC]) -> None:
        """Make ``npcs`` the roster the prompt lists and the answers are matched against."""
        self._roster = build_roster(npcs)

    def interpret_text(self, command: str, *, model_id: str) -> list[NpcOrder] | CommandRefused:
        """See ``TextOrderInterpreter``. The error's message names the failure type
        only; the failure's type and text go to the log."""
        messages = _build_text_messages(command, self._roster)
        return self._interpret(model=model_id, messages=messages, logged_input=command)

    def interpret_voice(self, audio: bytes, *, model_id: str) -> list[NpcOrder] | CommandRefused:
        """See ``VoiceOrderInterpreter`` and ``interpret_text``."""
        messages = _build_voice_messages(audio, self._roster)
        return self._interpret(model=model_id, messages=messages, logged_input="(audio input)")

    def _interpret(
        self,
        *,
        model: str,
        messages: list[ChatCompletionRequestMessageTypedDict],
        logged_input: str,
    ) -> list[NpcOrder] | CommandRefused:
        try:
            return self._ask(model=model, messages=messages, logged_input=logged_input)
        except Exception as error:
            failure = type(error).__name__
            logger.bind(event="order_interpretation", failure=failure).error(
                f"Mistral interpretation failed: {failure}: {error}"
            )
            message = f"Mistral could not interpret the command ({failure})"
            raise OrderInterpretationError(message) from error

    def _ask(
        self,
        *,
        model: str,
        messages: list[ChatCompletionRequestMessageTypedDict],
        logged_input: str,
    ) -> list[NpcOrder] | CommandRefused:
        self._pipeline_logger.llm_start(input_text=logged_input)
        try:
            response = self._client.chat.complete(
                model=model,
                messages=messages,
                tools=[ORDERS_TOOL],
                tool_choice="any",
                parallel_tool_calls=False,
                temperature=0.7,
                max_tokens=1024,
            )
        except Exception as error:
            self._pipeline_logger.llm_end(order=None, model=model, error=str(error))
            raise
        answer = read_orders_answer(response, self._roster)
        self._log_answer(response, answer, model=model)
        return answer

    def _log_answer(
        self,
        response: ChatCompletionResponse,
        answer: list[NpcOrder] | CommandRefused,
        *,
        model: str,
    ) -> None:
        usage = response.usage
        audio_seconds = usage.prompt_audio_seconds if usage else None
        log_call = partial(
            self._pipeline_logger.llm_end,
            prompt_tokens=(usage.prompt_tokens or 0) if usage else 0,
            completion_tokens=(usage.completion_tokens or 0) if usage else 0,
            audio_seconds=audio_seconds if isinstance(audio_seconds, int) else 0,
            model=model,
        )
        if isinstance(answer, CommandRefused):
            log_call(order=None, error=f"answer refused: {answer.reason}")
            return
        order = build_orders_for_log(answer)
        log_call(order=order)
        if answer:
            self._pipeline_logger.pipeline_summary(order=order)
