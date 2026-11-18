---
type: interface
title: HTTP and Socket.IO contract
description: The routes and events the browser uses, how request bodies are validated at the boundary, and the 400, 403 and 413 behaviour, including the origin guard.
tags: [http, socketio, validation, security, contract]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:30:24.405Z
sources:
  - id: openwiki-source-98b4fef5bee3b5a0d880f16b
    resource: repo://docs/api.md
  - id: openwiki-source-487fb4d406cec828c3ee91a7
    resource: repo://game/direct_orders.py
  - id: openwiki-source-141c86ea716204370c1b7a2d
    resource: repo://server/app.py
  - id: openwiki-source-be5f2d227c84deca728731ae
    resource: repo://server/constants.py
  - id: openwiki-source-a157882f393a5221cd3b727b
    resource: repo://server/request_bodies.py
  - id: openwiki-source-f7ec59fd0107dc945740979a
    resource: repo://server/routes.py
generated: { by: "claude-code", at: "2026-11-18T09:30:24.405Z" }
---

# HTTP and Socket.IO contract

The browser client and `server/routes.py` talk over HTTP and one Socket.IO event. The reference document is `docs/api.md`; a change to a route or payload updates both sides in the same PR. The server serves the client itself, so there is no CORS layer. See [Browser client](browser-client.md).

## Socket.IO

The only event is `state`, server to client, carrying the full game state. It is emitted on `connect` (`register_socket_events`) and by the game loop every third tick; see [Game loop and state push](../workflows/game-loop-and-state-push.md). `GET /api/state` returns the same shape.

## Routes

| Route | Body | Effect |
|---|---|---|
| `GET /api/state` | none | full state |
| `POST /api/action` | `{npcId, action, target?}` | enqueue a direct action |
| `POST /api/select` | `{npcId}` or `{}` | select one NPC or deselect all |
| `POST /api/move` | `{npcId, col, row}` | enqueue `move_to` |
| `POST /api/discard` | amounts per stored resource | discard from storage, returns `discarded` |
| `POST /api/dismiss_storage` | none | release NPCs waiting to deposit, returns `released` |
| `POST /api/audio` | multipart `audio` or JSON `audio_b64` | start voice command interpretation |

`GET /`, `/static/<path>` and `/favicon.ico` serve the client files with `send_from_directory`.

Each route calls one public `GameEngine` method, which takes the engine lock. See [Game loop and state push](../workflows/game-loop-and-state-push.md).

## Validation at the boundary

`server/request_bodies.py` parses each body once into a typed value and raises `InvalidRequestError`, which the blueprint turns into `400 {"error": ...}`. A request that fails never reaches `game/`.

- The body must be a JSON object. `_json_body` uses `get_json(silent=True)`, so a body that is not JSON, or not sent as `application/json`, reads as `None` and is refused. This deliberately avoids `force=True`, which would accept `text/plain` cross-site posts.
- Integers exclude booleans: `true` is not a number.
- `action` must be an `ActionType` value. `target` must be a list of two integers. A `move_to` without a target is refused when the `DirectOrder` is built.
- Discard keys must be stored resource kinds and amounts must not be negative.
- `audio_b64` must be strict base64.

After parsing, the engine's outcome decides the answer: an unknown `npcId` or a target outside the map is a 400. An NPC that cannot do an allowed-in-contract action still gets `200`, since the request was valid and the NPC says so in the game. `/api/audio` answers 400 below `MIN_AUDIO_BYTES` (100). The domain outcome is a value, so routes never parse messages. See [Voice order flow](../workflows/voice-order-flow.md).

## Origin guard and limits

- `before_request` answers `403` when a request has an `Origin` header that differs from the host the request reached. Browsers send `Origin` on cross-origin requests, including form and `text/plain` POSTs that skip preflight. A request without it, such as curl or the test client, passes.
- Flask's `MAX_CONTENT_LENGTH` is `MAX_REQUEST_BYTES` (4 MiB); a larger body gets `413` before it is read.
- Socket.IO keeps its default same-origin check.
- Not covered, per `docs/api.md`: reverse proxies (the HTTP check ignores `X-Forwarded-*`, Socket.IO honours it) and DNS rebinding.

## Related pages

- [System overview](../architecture/system-overview.md)
- [Running and configuration](../operations/running-and-configuration.md) for `G4AL_HOST`
