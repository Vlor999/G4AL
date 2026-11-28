# Client/server contract

The browser client in `static/` and the server (`server/routes.py`) talk over HTTP and Socket.IO. A change
to a route, an event or a payload updates both sides in the same PR
(`.claude/rules/server-style.md`). The server listens on `http://127.0.0.1:8000`.

## Socket.IO

| Event | Direction | Payload |
|---|---|---|
| `state` | server → client | full game state (same shape as `GET /api/state`), pushed every 3rd tick (~20 Hz) and once on `connect` |

### Storage

The `storage` object of the state holds the settlement stockpile:

| Key | Type | Meaning |
|---|---|---|
| `wood`, `stone`, `gold`, `wheat` | int | units stored per resource |
| `total` | int | units stored, all resources |
| `capacity` | int | maximum `total`: a base plus a bonus per completed house (`game/settings.py`) |
| `houseCount` | int | completed houses, the storage hut excluded |

The client shows `total / capacity` and `houseCount` in the inventory panel.

### Chat

`chat` lists the latest messages of the chat panel (`CHAT_HISTORY_LENGTH`,
`server/constants.py`), oldest first. Each entry has a `kind`:

| `kind` | Other keys | Meaning |
|---|---|---|
| `typed_command` | `text`: str | a command the player typed (`POST /api/command`) |
| `spoken_command` | none | a push-to-talk command (`POST /api/audio`): the interpreter hears the audio, so there is no text |
| `voice_line` | `npcName`: str, `text`: str | an NPC's answer to the command above it, shown whether or not ElevenLabs voices it |

### Models

The player picks the model that interprets the next command
(`api/model_catalog.py`, `server/model_selection.py`):

| Key | Type | Meaning |
|---|---|---|
| `models` | list of `{"id": str, "name": str, "hasVoiceInput": bool}` | the catalog models whose provider API key is set, in catalog order |
| `selectedModelId` | str | the `id` of the model the next command goes to |
| `hasVoiceInput` | bool | whether the selected model takes spoken commands |

When `hasVoiceInput` is `false`, the client hides the microphone prompt, push-to-talk
does nothing, and `POST /api/audio` answers 400. A command keeps the model selected
when it was sent, even if the player switches before its answer arrives.

### Map biomes

`map.biomes` is a `rows × cols` array of strings, indexed `[row][col]` like
`map.tiles`: the biome of each tile, one of `meadow`, `forest`, `highland`, `lake`
(`game/world/terrain.py`, generation in
[ADR 0003](adr/0003-biome-map-generation.md)). The client picks the grass tileset and
the bushes from it.

### Object dimensions

Every entry of `resources`, `npcs` and `fauna` carries the size of its kind
(`game/world/dimensions.py`, model in [ADR 0002](adr/0002-object-dimensions-and-height-model.md)).
All values are in tiles; the client multiplies them by `map.tileSize`.

| Field | Type | Meaning |
|---|---|---|
| `footprint` | `{"width": int, "depth": int}` | tiles covered on the grid, from `col`, `row` rightwards and downwards (one tile for anything but a structure) |
| `height` | number, multiple of 0.5 | how far the object rises above its footprint |
| `sprite` | `{"width", "height", "anchorX", "anchorY"}` numbers | rectangle the sprite is drawn in; `anchorX`, `anchorY` locate the ground point inside it from its top-left corner |

The ground point is the bottom centre of the footprint for a resource or a structure,
and `x`, `y` for an NPC or a creature. Structures no longer send `gridWidth` and
`gridHeight`: `footprint` replaces them.

### NPC lake actions

Besides its other fields, each entry of `npcs` carries what the client needs to draw
the lake actions (`go_to_shore`, `fish`, `swim`):

| Field | Type | Meaning |
|---|---|---|
| `isInWater` | bool | the NPC stands on a water tile: only during a swim |
| `waterTile` | `[col, row]` or `null` | the water tile next to the shore tile of the lake action under way; `null` outside one |
| `lastRefusal` | str or `null` | why the latest refused action was refused (`"no shore reachable"`), until the action after it ends; `null` otherwise |

The client draws a fishing pawn idle, facing `waterTile`, with a water splash on the
catch (when the `fish` action ends); a swimming NPC clipped at the waterline, with a
splash each time `isInWater` changes. Durations and who may do what come from the
server (`allowedActions`, `state`, `actionType`).

No client reads `lastRefusal` yet. [#123](https://github.com/Vlor999/G4AL/issues/123)
will return the refusal reason from `enqueue`, so the orders report it.

## HTTP

All POST bodies are JSON sent as `application/json` unless stated. A route parses its
body once (`server/request_bodies.py`) and answers:

- 200 `{"ok": true, ...}` on success;
- 400 `{"error": "<reason>"}` when the body is not a JSON object, or a field is
  missing, of the wrong type (`true` is not an integer) or out of range: an unknown
  `npcId` or `action`, a tile outside the map, a `target` that is not two integers;
- 403 `{"error": ...}` when a browser page of another origin sends the request (its
  `Origin` header differs from the host and port the request reached);
- 403 `{"error": "host not allowed"}` when the `Host` header is not an allowed host
  (see [Origins](#origins));
- 413 `{"error": ...}` when the body exceeds `MAX_REQUEST_BYTES` (4 MiB,
  `server/constants.py`), checked before the body is read.

| Route | Body | Effect |
|---|---|---|
| `GET /api/state` | none | returns the full game state |
| `POST /api/action` | `{"npcId": int, "action": str, "target"?: [col, row]}` | enqueues an action on an NPC; `action` is an `ActionType` value of `game/npcs/actions.py`; `target`, when given, must be two integers inside the map, whatever the action; `move_to` needs one, `build` and `plant_wheat` without one aim at the NPC's tile, the other actions (`go_to_shore`, `fish` and `swim` included) do not use it. An action the NPC is not allowed to do still answers 200: the NPC says so in the game |
| `POST /api/select` | `{"npcId": int}` or `{}` | selects an NPC, or deselects all |
| `POST /api/move` | `{"npcId": int, "col": int, "row": int}` | enqueues a `move_to` |
| `POST /api/discard` | `{"wood"?: int, "stone"?: int, "gold"?: int, "wheat"?: int}`, amounts ≥ 0, no other key | discards resources from storage; returns `discarded` |
| `POST /api/dismiss_storage` | none | releases NPCs waiting to deposit into a full storage; returns `released` |
| `POST /api/audio` | multipart field `audio` (WAV), or `{"audio_b64": str}` in standard base64 | sends a push-to-talk recording to the selected model; under 100 bytes of audio, or a selected model without voice input (`hasVoiceInput` false), answers 400; the resulting orders arrive through the next `state` events |
| `POST /api/command` | `{"text": str}` | sends a typed command to the selected model; `text` is stripped and must be neither empty nor longer than 500 characters (`MAX_COMMAND_CHARACTERS`, `server/constants.py`), or the route answers 400; the command shows in `chat` at once, the resulting orders and voice lines arrive through the next `state` events |
| `POST /api/model` | `{"modelId": str}` | selects the model of the next commands; an `id` outside `models` answers 400 |

## Origins

The client is served by the same server, so the routes send no CORS headers and the
Socket.IO server keeps its default origin check (same scheme, host and port as the
request).

Before both checks, every request, the Socket.IO handshake and the static files
included, must carry an allowed `Host` header (`server/host_allowlist.py`), or it
gets 403 `{"error": "host not allowed"}`. The allowed hosts follow `G4AL_HOST`, always
with port 8000. `G4AL_HOST` is read without brackets and with an IPv6 address
compressed (`[0:0:0:0:0:0:0:1]` reads as `::1`):

| `G4AL_HOST` | Allowed `Host` |
|---|---|
| unset, empty, `127.0.0.1`, `localhost` | `localhost:8000`, `127.0.0.1:8000` |
| `0.0.0.0`, `::` | `localhost:8000`, `127.0.0.1:8000` |
| `::1` | `localhost:8000`, `127.0.0.1:8000`, `[::1]:8000` |
| a network address or name (`192.168.1.20`) | that address with `:8000` |
| a link-local address with a zone id (`fe80::1%en0`) | none: the server refuses to start |

This blocks DNS rebinding: a page whose domain re-resolves to the server's address
sends its own domain as `Host`, and an `Origin` equal to it (none on a same-origin
`GET`), so the origin checks alone accept it. To play from another machine, set
`G4AL_HOST` to the address the players type; a wildcard bind accepts loopback only.

Limit: a reverse proxy is not supported. The `Host` the server receives must be an
allowed one, the HTTP origin check ignores `X-Forwarded-*`, while the Socket.IO check
honours them.

## Static files

`GET /` serves `static/index.html`, `GET /static/<path>` the client modules and
assets, `GET /favicon.ico` the SVG icon.
