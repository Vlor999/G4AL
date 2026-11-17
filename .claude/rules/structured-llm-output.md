---
paths:
  - "api/**/*.py"
---

# Structured LLM output: constrain the shape, never parse prose

When a Mistral call must return a value from a fixed set (an action) or a record with
known fields (an NPC order), constrain the output on the API side and validate it at
the boundary. Never rely on the prompt alone ("respond with ONLY the JSON", "no
markdown fences") and then repair the text (stripping fences, slicing strings).

Prompt-and-parse is fragile: the model wraps the JSON in fences, adds a preamble, or
returns an action the game does not know, and the parse silently drops the order.

## The pattern (Mistral SDK)

Pass a JSON schema with `response_format`, using `enum` for fixed sets, then validate
the result into domain types:

```python
ORDER_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "npc_orders",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "orders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "npc": {"type": "string"},
                            "action": {"type": "string", "enum": [a.value for a in ActionType]},
                            "reply": {"type": "string"},
                        },
                        "required": ["npc", "action", "reply"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["orders"],
            "additionalProperties": False,
        },
    },
}

response = client.chat.complete(model=..., messages=..., response_format=ORDER_SCHEMA)
```

Forcing a tool call (`tools=[...]`, `tool_choice="any"`) is the alternative when the
model must pick between several shapes. Check the current Mistral docs for which
models (Voxtral included) support each mode before relying on it.

## Rules

- ❌ A prompt that carries the output format as parseable instructions, then
  `raw.strip("`")`.
- ✅ `response_format` with a JSON schema (or a forced tool), validated into a
  dataclass at the boundary.
- The prompt describes how to decide each field, not the output syntax.
- The allowed actions in the schema come from the domain enum, never from a second
  hand-written list; a test fails if they drift.
- An answer that fails validation is a named outcome (`order refused: unknown
  action`), logged and reported to the player, never a silent `None`.

`api/interpreter.py` predates this rule (prompt-and-parse with fence stripping); it
migrates in its own PR.
