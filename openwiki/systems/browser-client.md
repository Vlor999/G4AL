---
type: system
title: Browser client
description: How the static/ client is organised as classic scripts sharing one global namespace, what each script owns, and how it talks to the server, including the chat panel, the model picker and push-to-talk.
tags: [client, javascript, canvas, push-to-talk, chat]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-25T15:38:15.273Z
sources:
  - id: openwiki-source-ad8a0f8b85e961c2b13636c0
    resource: repo://server/serialization.py
  - id: openwiki-source-c961c7ffc2f8749373770f80
    resource: repo://static/chat.js
  - id: openwiki-source-f46176ec002caa739e9d3b36
    resource: repo://static/game.js
  - id: openwiki-source-fd46daa25ea84f5218478698
    resource: repo://static/index.html
  - id: openwiki-source-b647b77d0e23709a4ec3084c
    resource: repo://static/input.js
  - id: openwiki-source-faff17f71a0e062ed64b4611
    resource: repo://static/ptt.js
  - id: openwiki-source-0defe4441d6166e9778f1416
    resource: repo://static/renderer.js
  - id: openwiki-source-546d715933eb378ce5631982
    resource: repo://static/sprites.js
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
---

# Browser client

The client in `static/` is plain browser JavaScript with no build step and no `import` or `export`. `static/index.html` loads the scripts in order and they share one global, `window.G4AL`, which each file captures as `G` in an IIFE. Adding an `import` to one file would break the page.

## Scripts and load order

`index.html` loads the Socket.IO client from a CDN, then:

| Order | File | Owns |
|---|---|---|
| 1 | `assets/details.js` | Sprite configuration (`SPRITE_CONFIG`) |
| 2 | `sprites.js` | Creates `window.G4AL` and its shared state, the `postJSON` helper, sprite loading and animation tiers |
| 3 | `map_image.js` | `G.buildMapImage`: ground tiles drawn once per biome, decorations and clouds |
| 4 | `renderer.js` | Canvas drawing each animation frame (the largest file, about 850 lines) |
| 5 | `ptt.js` | Push-to-talk recording and WAV conversion |
| 6 | `ui.js` | Panels: roster, action buttons, game log, speech bubbles, storage alerts, discard, guide |
| 7 | `chat.js` | Chat panel (typed commands, chat history) and model picker |
| 8 | `input.js` | Keyboard, mouse and click handlers |
| 9 | `game.js` | Entry point: Socket.IO connection, camera, boot |

## State

The client keeps only view state: camera position, the selected NPC id, the pressed keys, the cached map and its pre-drawn image. The game state itself is whatever the last Socket.IO `state` event carried; `game.js` stores it in `G.gameState`, caches `map` from the first state and builds the map image from it (tiles and biomes). See [HTTP and Socket.IO contract](http-and-socketio-contract.md), [Game loop and state push](../workflows/game-loop-and-state-push.md) and [World and map generation](world-and-map-generation.md).

The renderer sizes and anchors sprites from the `footprint`, `height` and `sprite` box the server sends for each resource, NPC and creature, so object sizes live on the server only.

## Input

- WASD and arrow keys move the camera. Arrow keys have their default scrolling prevented.
- Keys pressed in a form field (the chat input, the model picker) belong to that field: they never move the camera or start push-to-talk.
- Holding `G` starts push-to-talk and releasing it stops the recording, but only when the state says `hasVoiceInput` (the selected model hears audio).
- Left click selects a controllable NPC within 30 pixels and posts `/api/select`; clicking elsewhere deselects with `{}`. Clicking a roster entry selects that NPC.
- Right click posts `/api/move` with the clicked tile for the selected NPC.
- Action buttons post `/api/action` with the selected id and the button's `data-action`.

## Chat panel and model picker (`chat.js`)

- Submitting the chat form posts the trimmed text to `/api/command`. See [Voice and typed order flow](../workflows/voice-order-flow.md).
- The panel renders the state's `chat` list: a typed command shows its text, a spoken command shows a microphone mark, and an NPC voice line shows the NPC name and its line. All text is HTML-escaped.
- The model picker lists the state's `models`, marking those with voice input, and posts `/api/model` on change. While the picker has focus, the pushed state does not overwrite the player's pick.
- `ui.js` calls `G.updateChat()` on each UI update and hides the microphone hint when the selected model has no voice input.

## Push-to-talk (`ptt.js`)

`pttStart` asks for the microphone, records with `MediaRecorder` (preferring webm opus), and on stop converts the clip to 16 kHz mono 16-bit PCM WAV with an `AudioContext`. It posts the WAV as multipart field `audio` to `/api/audio`. If decoding fails it uploads the raw blob. See [Voice and typed order flow](../workflows/voice-order-flow.md).

## Related pages

- [Quickstart](../quickstart.md)
- [System overview](../architecture/system-overview.md)
- [LLM models and providers](llm-models-and-providers.md)
