# Client/server contract

The browser client in `static/` and the server (`server/routes.py`) talk over HTTP and Socket.IO. A change
to a route, an event or a payload updates both sides in the same PR
(`.claude/rules/server-style.md`). The server listens on `http://127.0.0.1:8000`.

## Socket.IO

| Event | Direction | Payload |
|---|---|---|
| `state` | server → client | full game state (same shape as `GET /api/state`), pushed every 3rd tick (~20 Hz) and once on `connect` |

## HTTP

All POST bodies are JSON sent as `application/json` unless stated. A route parses its
body once (`server/request_bodies.py`) and answers:

- 200 `{"ok": true, ...}` on success;
- 400 `{"error": "<reason>"}` when the body is not a JSON object, or a field is
  missing, of the wrong type (`true` is not an integer) or out of range: an unknown
  `npcId` or `action`, a tile outside the map, a `target` that is not two integers;
- 413 `{"error": ...}` when the body exceeds `MAX_REQUEST_BYTES` (4 MiB,
  `server/constants.py`), checked before the body is read.

| Route | Body | Effect |
|---|---|---|
| `GET /api/state` | none | returns the full game state |
| `POST /api/action` | `{"npcId": int, "action": str, "target"?: [col, row]}` | enqueues an action on an NPC; `action` is an `ActionType` value of `game/actions.py`; `target`, when given, must be two integers inside the map, whatever the action; `move_to` needs one, `build` and `plant_wheat` without one aim at the NPC's tile, the other actions do not use it. An action the NPC is not allowed to do still answers 200: the NPC says so in the game |
| `POST /api/select` | `{"npcId": int}` or `{}` | selects an NPC, or deselects all |
| `POST /api/move` | `{"npcId": int, "col": int, "row": int}` | enqueues a `move_to` |
| `POST /api/discard` | `{"wood"?: int, "stone"?: int, "gold"?: int, "wheat"?: int}`, amounts ≥ 0, no other key | discards resources from storage; returns `discarded` |
| `POST /api/dismiss_storage` | none | releases NPCs waiting to deposit into a full storage; returns `released` |
| `POST /api/audio` | multipart field `audio` (WAV), or `{"audio_b64": str}` in standard base64 | sends a push-to-talk recording to Voxtral; under 100 bytes of audio answers 400; the resulting orders arrive through the next `state` events |

## Static files

`GET /` serves `static/index.html`, `GET /static/<path>` the client modules and
assets, `GET /favicon.ico` the SVG icon.
