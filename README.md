# G4AL

G4AL (Game For All) is a top-down 2D survival game you play with your voice. Hold a key, speak an order into your microphone, and Mistral's Voxtral model turns the audio into structured actions for your NPCs: chop wood, mine rock, build structures, plant wheat, defend the base. Each NPC has its own personality and answers with a voice line through ElevenLabs text-to-speech.

It was built for the Mistral Worldwide Hackathon 2026. The backend runs locally because hosting Voxtral and ElevenLabs calls for other players would cost too much in API fees.

## Features

| Feature | Details |
|---|---|
| Voice commands | Push-to-talk in the browser. The audio goes to Voxtral, which answers with a function call whose JSON schema lists the game's actions. |
| NPC personalities | Each NPC has a name, a personality and an ElevenLabs voice. |
| Survival | Chop wood, mine rock, plant and harvest wheat, build structures, manage hunger. |
| Combat | Archers shoot enemies. Wild archers attack from the map edges. |
| Web UI | A Flask and Socket.IO backend pushes game state to an HTML5 Canvas client at about 60 FPS. |
| Logging | Every voice command and LLM call is logged with timing, cost and token usage (JSONL). |

## Architecture

```
Browser (HTML5 Canvas + Socket.IO)
        |  WebSocket (state push + events)
Flask + Socket.IO server (server/)
        |-- Game engine      map, NPCs, entities, resources, combat   (game/)
        |-- Mistral Voxtral  audio -> structured NPC orders           (api/interpreter.py)
        |-- ElevenLabs TTS   NPC voice line playback                  (api/tts.py)
        `-- Pipeline logger  structured logs                          (api/logger.py)
```

## Setup

You need:

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- A Mistral API key from [console.mistral.ai](https://console.mistral.ai/)
- Optionally, an ElevenLabs API key from [elevenlabs.io](https://elevenlabs.io/). Without it the NPCs do not speak aloud.

```bash
git clone https://github.com/Vlor999/G4AL.git
cd G4AL
make install        # uv sync + pre-commit hooks
cp .env.example .env
```

Put your keys in `.env`:

```dotenv
MISTRAL_API_KEY="your-mistral-api-key"
ELEVENLABS_API_KEY="your-elevenlabs-api-key"   # optional
```

## Run

```bash
make run            # same as: uv run python main.py
```

Open http://127.0.0.1:8000 in your browser. The server listens on port 8000 on `127.0.0.1`; set `G4AL_HOST=0.0.0.0` to listen on all interfaces.

## Controls

| Input | Action |
|---|---|
| WASD or arrow keys | Move the camera |
| Hold G | Push-to-talk: record a voice command |
| Click an NPC | Select it |

Example voice commands:

- "Bob, go chop some wood near the forest"
- "Paul, build a house next to the storage hut"
- "Thomas, plant wheat south of the camp"
- "Archers, defend the base!"

## Project structure

```
main.py             entry point, starts the server
server/
  app.py            loads .env, builds the adapters and the Flask + Socket.IO app, starts the server
  engine.py         GameEngine and its game loop thread
  routes.py         HTTP routes and Socket.IO events
  serialization.py  game state -> client JSON
Makefile            install, run, check (format, lint, import contract, types, dead code, tests) and fix targets
pyproject.toml      dependencies
.env.example        environment variable template

api/
  interpreter.py    Voxtral audio -> structured NPC orders
  tts.py            ElevenLabs text-to-speech
  roster.py         NPC profiles (name, personality, voice)
  logger.py         pipeline logging, written to logs/

game/
  map.py            procedural tile map
  actions.py        NPC actions and action-machine states
  npc_base.py       shared NPC core: stats, queue, movement, hut trips
  npc.py            pawn action planning
  archer.py         archer combat
  pathfinding.py    A* on the tile grid
  npc_names.py      canonical NPC names and name picking
  ports.py          protocols the domain needs from the outside world
  entities.py       trees, rocks, structures, wheat fields
  creatures.py      sheep and wild archers
  storage.py        resource storage (wood, stone, gold, wheat)
  settings.py       game constants

static/
  game.js           client entry point, Socket.IO, camera
  renderer.js       canvas rendering
  sprites.js        sprite loading
  input.js          keyboard and mouse input
  ptt.js            browser push-to-talk recording
  ui.js             HUD and overlays
  assets/           sprite sheets and tilesets

tests/              pytest suite; tests/e2e drives the HTTP routes
docs/               architecture, client/server contract, decisions
```

Contributors and coding agents start with [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

Sprites and tilesets come from [Pixel Frog on itch.io](https://itch.io/profile/pixelfrog-assets).

## License

[MIT](LICENSE)
