# Security policy

## Supported versions

Only the latest commit on `main` is supported.

## Reporting a vulnerability

Do not open a public issue. Use GitHub's private vulnerability reporting
(**Security → Report a vulnerability** on the repository). You will get an answer
within a week.

## Scope

G4AL runs locally with your own Mistral and ElevenLabs API keys. Relevant reports
include key leakage (logs, client payloads, error messages), unvalidated input on the
HTTP or Socket.IO endpoints, and path traversal through the static file routes.
