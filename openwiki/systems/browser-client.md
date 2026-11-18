---
type: system
title: Browser client
description: How the static/ client is organised as classic scripts sharing one global namespace, what each script owns, and how it talks to the server.
tags: [client, javascript, canvas, push-to-talk]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:30:24.405Z
sources:
  - id: openwiki-source-f46176ec002caa739e9d3b36
    resource: repo://static/game.js
  - id: openwiki-source-fd46daa25ea84f5218478698
    resource: repo://static/index.html
  - id: openwiki-source-b647b77d0e23709a4ec3084c
    resource: repo://static/input.js
  - id: openwiki-source-faff17f71a0e062ed64b4611
    resource: repo://static/ptt.js
generated: { by: "claude-code", at: "2026-11-18T09:30:24.405Z" }
---

# Browser client

The client in `static/` is plain browser JavaScript with no build step and no `import` or `export`. `static/index.html` loads the scripts in order and they share one global, `window.G4AL`, which each file captures as `G` in an IIFE. Adding an `import` to one file would break the page.

## Scripts and load order

`index.html` loads the Socket.IO client from a CDN, then:

| Order | File | Owns |
|---|---|---|
| 1 | `assets/details.js` | Sprite configuration (`SPRITE_CONFIG`) |
| 2 | `sprites.js` | Creates `window.G4AL`, the `postJSON` helper, sprite loading and animation tiers |
| 3 | `renderer.js` | Canvas drawing (the largest file, about 950 lines) |
| 4 | `ptt.js` | Push-to-talk recording and WAV conversion |
| 5 | `ui.js` | Panels: roster, action buttons, storage alerts, discard |
| 6 | `input.js` | Keyboard, mouse and click handlers |
| 7 | `game.js` | Entry point: Socket.IO connection, camera, canvas sizing, boot |

## State

The client keeps only view state: camera position, the selected NPC id, the pressed keys, the cached map. The game state itself is whatever the last Socket.IO `state` event carried; `game.js` stores it in `G.gameState` and builds the map image once from the first state. See [HTTP and Socket.IO contract](http-and-socketio-contract.md) and [Game loop and state push](../workflows/game-loop-and-state-push.md).

## Input

- WASD and arrow keys move the camera.
- Holding `G` starts push-to-talk and releasing it stops the recording (`input.js` calls `G.pttStart` and `G.pttStop`).
- Left click selects a controllable NPC within 30 pixels and posts `/api/select`; clicking elsewhere deselects with `{}`.
- Right click posts `/api/move` with the clicked tile for the selected NPC.
- Action buttons post `/api/action` with the selected id and the button's `data-action`.

## Push-to-talk (`ptt.js`)

`pttStart` asks for the microphone, records with `MediaRecorder` (preferring webm opus), and on stop converts the clip to 16 kHz mono 16-bit PCM WAV with an `AudioContext`. It posts the WAV as multipart field `audio` to `/api/audio`. If decoding fails it uploads the raw blob. See [Voice order flow](../workflows/voice-order-flow.md).

## Related pages

- [Quickstart](../quickstart.md)
- [System overview](../architecture/system-overview.md)
