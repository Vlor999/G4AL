"""Meaningful literals of the adapters (tool names, prices, masks); the models and
their prices live in ``api/model_catalog.py``."""

ELEVENLABS_API_KEY_MASK = "<ELEVENLABS_API_KEY>"
"""What a TTS log line shows in place of the ElevenLabs API key when an error text holds it."""

# ElevenLabs TTS price (varies by plan; usage-based estimate), in USD per character.
# Source: https://elevenlabs.io/pricing
TTS_COST_PER_CHAR = 0.30 / 1_000

# Sampling of the order interpreter's chat completion.
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 1024

# ElevenLabs audio of a voice line: mp3, 22.05 kHz, 32 kbps.
TTS_OUTPUT_FORMAT = "mp3_22050_32"
# Seconds the TTS worker waits on its queue before it checks again whether to stop.
TTS_QUEUE_POLL_SECONDS = 0.5

ORDERS_TOOL_NAME = "give_npc_orders"
"""Function the model is forced to call (``tool_choice="any"``) to give the orders."""
