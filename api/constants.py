"""Meaningful literals of the adapters (vendor model names, tool names)."""

AUDIO_MODEL = "voxtral-small-latest"
"""Mistral model that hears the spoken command and answers with the orders tool call."""

ELEVENLABS_API_KEY_MASK = "<ELEVENLABS_API_KEY>"
"""What a TTS log line shows in place of the ElevenLabs API key when an error text holds it."""

# Voxtral Small token prices, in USD per token. Source, read 2026-11-18:
# https://docs.mistral.ai/models/voxtral-small-25-07 (names voxtral-small-2507 and
# voxtral-small-latest): $0.1 / M input tokens, $0.4 / M output tokens, $0.004 / min audio.
# The logged `cost_usd` of a Voxtral call covers tokens only; the audio minutes are not
# priced yet.
AUDIO_MODEL_INPUT_COST_PER_TOKEN = 0.1 / 1_000_000
AUDIO_MODEL_OUTPUT_COST_PER_TOKEN = 0.4 / 1_000_000

# ElevenLabs TTS price (varies by plan; usage-based estimate), in USD per character.
# Source: https://elevenlabs.io/pricing
TTS_COST_PER_CHAR = 0.30 / 1_000

ORDERS_TOOL_NAME = "give_npc_orders"
"""Function Voxtral is forced to call (``tool_choice="any"``) to give the orders."""
