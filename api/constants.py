"""Meaningful literals of the adapters (vendor model names, tool names)."""

AUDIO_MODEL = "voxtral-small-latest"
"""Mistral model that hears the spoken command and answers with the orders tool call."""

ELEVENLABS_API_KEY_MASK = "<ELEVENLABS_API_KEY>"
"""What a TTS log line shows in place of the ElevenLabs API key when an error text holds it."""

ORDERS_TOOL_NAME = "give_npc_orders"
"""Function Voxtral is forced to call (``tool_choice="any"``) to give the orders."""
