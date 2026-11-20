"""Meaningful literals of the adapters (tool names, prices, masks); the models and
their prices live in ``api/model_catalog.py``."""

ELEVENLABS_API_KEY_MASK = "<ELEVENLABS_API_KEY>"
"""What a TTS log line shows in place of the ElevenLabs API key when an error text holds it."""

# ElevenLabs TTS price (varies by plan; usage-based estimate), in USD per character.
# Source: https://elevenlabs.io/pricing
TTS_COST_PER_CHAR = 0.30 / 1_000

ORDERS_TOOL_NAME = "give_npc_orders"
"""Function the model is forced to call (``tool_choice="any"``) to give the orders."""
