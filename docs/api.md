# Client/server contract

The browser client in `static/` and `server.py` talk over HTTP and Socket.IO. A change
to a route, an event or a payload updates both sides in the same PR
(`.claude/rules/server-style.md`). The server listens on `http://127.0.0.1:8000`.

## Socket.IO

| Event | Direction | Payload |
|---|---|---|
| `state` | server → client | full game state (same shape as `GET /api/state`), pushed every tick and once on `connect` |

## HTTP

All POST bodies are JSON unless stated. Every route answers `{"ok": true, ...}` on
success and `{"error": "<reason>"}` with status 400 on a bad request.

| Route | Body | Effect |
|---|---|---|
| `GET /api/state` | none | returns the full game state |
| `POST /api/action` | `{"npcId": int, "action": str, "target": [col, row]?}` | enqueues an action on an NPC; `action` is one of the `VALID_ACTIONS` of `api/interpreter.py` |
| `POST /api/select` | `{"npcId": int}` or `{}` | selects an NPC, or deselects all |
| `POST /api/move` | `{"npcId": int, "col": int, "row": int}` | enqueues a `move_to` |
| `POST /api/discard` | `{"wood"?: int, "stone"?: int, "gold"?: int, "wheat"?: int}` | discards resources from storage; returns `discarded` |
| `POST /api/dismiss_storage` | none | releases NPCs waiting to deposit into a full storage; returns `released` |
| `POST /api/audio` | multipart field `audio` (WAV), or `{"audio_b64": str}` | sends a push-to-talk recording to Voxtral; the resulting orders arrive through the next `state` events |

## Static files

`GET /` serves `static/index.html`, `GET /static/<path>` the client modules and
assets, `GET /favicon.ico` the SVG icon.
