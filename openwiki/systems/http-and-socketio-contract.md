---
type: interface
title: HTTP and Socket.IO contract
description: The routes and events the browser uses, how request bodies are validated at the boundary, the Host allowlist and origin guard, and the 400, 403 and 413 behaviour.
tags: [http, socketio, validation, security, contract]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-28T12:48:19.642Z
sources:
  - id: openwiki-source-98b4fef5bee3b5a0d880f16b
    resource: repo://docs/api.md
  - id: openwiki-source-46a12a4841927745353b96bf
    resource: repo://game/orders/direct_orders.py
  - id: openwiki-source-141c86ea716204370c1b7a2d
    resource: repo://server/app.py
  - id: openwiki-source-be5f2d227c84deca728731ae
    resource: repo://server/constants.py
  - id: openwiki-source-1c24919bb4b6d54036334bad
    resource: repo://server/host_allowlist.py
  - id: openwiki-source-b4711c804efbd2e1bf190ccf
    resource: repo://server/model_selection.py
  - id: openwiki-source-a157882f393a5221cd3b727b
    resource: repo://server/request_bodies.py
  - id: openwiki-source-f7ec59fd0107dc945740979a
    resource: repo://server/routes.py
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
---

# HTTP and Socket.IO contract

The browser client and `server/routes.py` talk over HTTP and one Socket.IO event. The reference document is `docs/api.md`; a change to a route or payload updates both sides in the same PR. The server serves the client itself, so there is no CORS layer. See [Browser client](browser-client.md).

## Socket.IO

The only event is `state`, server to client, carrying the full game state. It is emitted on `connect` (`register_socket_events`) and by the game loop every third tick; see [Game loop and state push](../workflows/game-loop-and-state-push.md). `GET /api/state` returns the same shape, including `chat`, `models`, `selectedModelId` and `hasVoiceInput`.

## Routes

| Route | Body | Effect |
|---|---|---|
| `GET /api/state` | none | full state |
| `POST /api/action` | `{npcId, action, target?}` | enqueue a direct action |
| `POST /api/select` | `{npcId}` or `{}` | select one NPC or deselect all; an unknown `npcId` is a 400 |
| `POST /api/move` | `{npcId, col, row}` | enqueue `move_to` |
| `POST /api/discard` | amounts per stored resource | discard from storage, returns `discarded` |
| `POST /api/dismiss_storage` | none | release NPCs waiting to deposit, returns `released` |
| `POST /api/audio` | multipart `audio` or JSON `audio_b64` | send a voice command to the selected model |
| `POST /api/command` | `{text}` | send a typed command to the selected model |
| `POST /api/model` | `{modelId}` | pick the model of the next commands |

`GET /`, `/static/<path>` and `/favicon.ico` serve the client files with `send_from_directory`.

Each route calls one public `GameEngine` method, which takes the engine lock or the model selection's lock. See [Game loop and state push](../workflows/game-loop-and-state-push.md) and [LLM models and providers](llm-models-and-providers.md).

## Validation at the boundary

`server/request_bodies.py` parses each body once into a typed value and raises `InvalidRequestError`, which the blueprint turns into `400 {"error": ...}`. A request that fails never reaches `game/`.

- The body must be a JSON object. `_json_body` uses `get_json(silent=True)`, so a body that is not JSON, or not sent as `application/json`, reads as `None` and is refused. This deliberately avoids `force=True`, which would accept `text/plain` cross-site posts.
- Integers exclude booleans: `true` is not a number.
- `action` must be an `ActionType` value. `target` must be a list of two integers. A `move_to` without a target is refused when the `DirectOrder` is built.
- Discard keys must be stored resource kinds and amounts must not be negative.
- `audio_b64` must be strict base64.
- `text` is stripped and must be neither empty nor longer than `MAX_COMMAND_CHARACTERS` (500).
- `modelId` must be a string.

After parsing, the engine's answer decides the response:

- An unknown `npcId` or a target outside the map is a 400.
- An NPC that cannot do the action still gets `200`, since the request was valid and the NPC says so in the game.
- `/api/audio` answers 400 below `MIN_AUDIO_BYTES` (100), and when the selected model takes no voice commands.
- `/api/model` answers 400 for an id outside the available models.

The domain outcome is a value, so routes never parse messages. See [Voice and typed order flow](../workflows/voice-order-flow.md).

## Host allowlist, origin guard and limits

- **Host allowlist.** `HostAllowlistMiddleware` wraps the whole WSGI app, Socket.IO and static files included, and answers `403 {"error": "host not allowed"}` when the `Host` header is not allowed. The allowed hosts follow `G4AL_HOST`, always with port 8000: `localhost` and `127.0.0.1` when the server listens on loopback (a loopback or wildcard bind), plus the bind address itself unless it is a wildcard. This blocks DNS rebinding, where a page whose domain re-resolves to the server sends its own domain as `Host` and an equal `Origin`. See [Running and configuration](../operations/running-and-configuration.md).
- **Origin guard.** `before_request` answers `403` when a request has an `Origin` header that differs from the host the request reached. Browsers send `Origin` on cross-origin requests, including form and `text/plain` POSTs that skip preflight. A request without it, such as curl or the test client, passes.
- **Size.** Flask's `MAX_CONTENT_LENGTH` is `MAX_REQUEST_BYTES` (4 MiB); a larger body gets `413` before it is read.
- Socket.IO keeps its default same-origin check.
- Not supported, per `docs/api.md`: reverse proxies. The received `Host` must be an allowed one, and the HTTP origin check ignores `X-Forwarded-*` while Socket.IO honours it.

## Related pages

- [System overview](../architecture/system-overview.md)
- [Running and configuration](../operations/running-and-configuration.md) for `G4AL_HOST`
