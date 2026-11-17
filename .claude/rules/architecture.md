# Architecture of application code

Applies to every PR that adds or changes Python application code (`game/`, `api/`,
`server.py`, `main.py`, scripts). The frontend (`static/`) follows the last section.
The principles come from the `ub-mode` skill (`~/.claude/skills/ub-mode/SKILL.md`)
when it is installed; this file wins where they differ.

## Layers

| Layer | Lives in | Holds | Imports |
|---|---|---|---|
| Domain | `game/` | the simulation: map, NPCs and their action queue, fauna, resources, storage, pathfinding, game rules and tuning (`game/settings.py`) | `game/` only, standard library |
| Ports | `game/ports.py` (create it with the first one) | every `Protocol` the domain needs from the outside world (an order source, a voice line sink, a clock) and their errors | domain types |
| Adapters | `api/` | one module per external system: Mistral Voxtral (`interpreter.py`), ElevenLabs + pygame mixer (`tts.py`), log files (`logger.py`) | ports, domain types, constants |
| Entry point | `server.py`, `main.py` | builds the adapters, owns the game loop thread, maps HTTP/Socket.IO payloads to domain calls and domain state to JSON | everything |
| Client | `static/` | rendering, input, push-to-talk capture | the server's HTTP and Socket.IO contract only |

- The domain does no I/O: no Flask, Socket.IO, Mistral, ElevenLabs, pygame, `print`,
  file, environment or network access in `game/`. What it needs from outside comes
  through a port or an injected value.
- The domain writes no vendor format: no JSON payload shape for the client, no prompt
  text, no Mistral message structure. It hands values over; the entry point or the
  adapter renders them.
- A port is named after a capability (`OrderInterpreter`, `VoiceLineSpeaker`) and its
  methods after game actions (`interpret`, `speak`), never after vendor calls.
- An adapter holds no game rule, translates every vendor error into its port's error,
  and never puts a secret in an error or a log line.
- The entry point holds no game decision. A rule that lives in `server.py`
  (`GameEngine`) today moves to `game/` when a PR touches it.
- Smallest design that holds these rules: a type exists when it carries a rule or a
  validation, a module when it has its own role.

## Rules

1. One decision lives in one place. The client never re-implements a server rule
   (costs, ranges, capacities): it renders what the state says.
2. Dependencies are injected. Tests pass fakes of the ports; patching a module global
   means an injection is missing.
3. Outside data is parsed once, at the boundary, into domain types: an LLM answer in
   `api/interpreter.py`, a request body in the Flask route. A bad record is refused
   there and never reaches `game/`.
4. Types make illegal states impossible. A value with a bound (a tile coordinate, an
   amount) is checked where it is built. Distinct cases are a union or an enum, not
   optional fields.
5. A domain step returns its outcome as a value (done, refused with a reason). The
   entry point reads the value and never parses an error message.
6. Game tuning numbers live in `game/settings.py`; other meaningful literals go in the
   package's `constants.py`.

## Code

These apply to what a PR adds or renames; older code follows through its own PR.

- Names say what the function does or returns, in game terms and full words. One
  concept has one name in every layer (`npc`, `structure`, `storage`), on the server
  and in `static/`.
- At most two positional parameters, `self` and `cls` excluded; the others after `*`.
  Tests, `Protocol` implementations and dataclasses are exempt.
- Docstrings on public functions and types when the signature does not tell the
  caller everything (see `language.md`).

## Tests

- Domain tests build their world by hand (map, NPCs, resources) and use fakes of the
  ports. No network, no audio device, no running server.
- A rule is tested once, at its layer, its cases in one parametrized test.
- A bug fix comes with the test that would have caught it.

## Design before code

Before coding a non-trivial change, write the plan as a table of layer, module and
role. Before the push, check imports against the layer table, grep `game/` for vendor
imports (`flask`, `mistralai`, `elevenlabs`, `pygame`), list the functions with more
than two positional parameters, and run the quality gates.

## Quality gates

From the repository root:

```bash
make check
```

It runs `ruff format --check`, `ruff check`, `mypy` (strict), `vulture` and `pytest`
with coverage. When `ub-mode` is installed, also run its CRAP and duplication gates on
the changed files:

```bash
uv run --script ~/.claude/skills/ub-mode/scripts/quality.py --base origin/main --tests tests
```

- **CRAP < 10** for every function of a changed file.
- **No duplicate pair ≥ 0.8** that involves a changed file.

A failing gate is fixed, or the PR explains the exception. Code the branch does not
touch never blocks.

## Frontend (`static/`)

- Plain ES modules, no build step. A module owns one concern (`renderer.js` draws,
  `input.js` reads input, `ptt.js` records, `ui.js` builds panels, `sprites.js` loads
  assets).
- The game state comes from the server; the client keeps only view state (camera,
  hover, selection highlight).
- Same naming rules as Python, in camelCase.
