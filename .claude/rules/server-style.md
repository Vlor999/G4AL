---
paths:
  - "server/**/*.py"
---

# Server style (Flask + Socket.IO)

- A route parses its body once into typed values, answers 400 on a missing or
  out-of-range field, and calls one `GameEngine` / domain method. It holds no game
  rule.
- Every mutation of game state from a route or a Socket.IO handler goes through the
  engine's lock or queue: the game loop runs in its own thread.
- Blocking calls (Mistral, ElevenLabs) never run on the game loop thread or inside a
  request handler; they run in a worker thread and hand their result back to the loop.
- The HTTP routes and Socket.IO events are a contract with `static/`. A rename or a
  payload change updates both sides in the same PR.
- Upload size is bounded (`MAX_CONTENT_LENGTH`) and checked before reading the body.
