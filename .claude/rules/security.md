# Security: universal rules

Apply to every source file, config file and doc.

## Secrets

- Never hardcode an API key or token. Keys come from `.env` (`MISTRAL_API_KEY`,
  `ELEVENLABS_API_KEY`), loaded once in the entry point; `.env.example` lists every
  variable with a placeholder value.
- Never log or print a full key, not even in debug. Truncate (`key[:4]`) or log
  whether it is set.
- `gitleaks` runs in pre-commit and CI. A finding is fixed by removing the secret and
  rotating the key, never by an allowlist entry for a real secret.

## Player data

- Recorded audio is sent to Mistral and never written to disk.
- Logs (`logs/`, ignored by git) hold transcripts, orders and costs, never audio or
  keys.

## Server surface

- The server binds to `127.0.0.1` by default. Exposing it on a network is an explicit
  opt-in through the environment, documented in the README.
- Every route that reads a body validates it at the boundary: required fields, types,
  ranges (an `npcId` that exists, a `col`/`row` inside the map), and a size limit for
  uploads (`/api/audio`). A bad request gets a 400, never a stack trace.
- `send_from_directory` only; never build a filesystem path from request data.
- LLM output is untrusted input: it is parsed against the allowed actions before
  anything reaches the game (`structured-llm-output.md`).

## Dependencies

- New dependencies go through `uv add` (runtime) or `uv add --dev` (tooling), and
  `uv.lock` is committed with them.
- Dependabot PRs and `pip-audit` findings in CI are handled, not dismissed.
