# 🏰 G4AL — Game For All - Vibe Gaming

> **Mistral Worldwide Hackathon 2026** — A voice-controlled 2D survival game powered by Mistral AI

G4AL is a top-down 2D survival game where you command NPCs using **your voice**. Speak naturally into your microphone, and Mistral's **Voxtral** model interprets your orders into structured game actions — chopping wood, mining rocks, building structures, planting wheat, defending against enemies, and more. Each NPC has its own personality and responds with in-character voice lines via **ElevenLabs TTS**.

---
## 🎤 Voice-First Gaming — A New Frontier

G4AL pioneers a revolutionary approach to game interaction: **pure voice control**. By eliminating traditional input devices, we're opening gaming to players with mobility impairments, visual disabilities, or anyone seeking hands-free immersion.

This voice-first paradigm demonstrates how AI can democratize gaming:
- **Accessibility**: Players with limited motor control can fully engage through natural speech
- **Inclusivity**: Voice commands work across age groups and technical skill levels
- **Immersion**: Speaking to NPCs feels more natural than clicking buttons

G4AL is just the beginning. This foundation paves the way for future titles to embrace voice as a primary interaction model, proving that speech-driven gameplay isn't a gimmick—it's a gateway to more inclusive, innovative entertainment.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Voice Commands** | Push-to-talk in the browser — audio is sent to Voxtral (multimodal audio+text → structured JSON) |
| **NPC Personalities** | Each NPC has a unique name, soul/personality, and ElevenLabs voice |
| **Survival Gameplay** | Chop wood, mine rock, plant & harvest wheat, build structures, manage hunger |
| **Combat** | Archers can shoot enemies; wild archers attack from the map edges |
| **Real-time Web UI** | Flask + Socket.IO backend pushes game state at ~60 FPS to an HTML5 Canvas client |
| **Structured Logging** | Every voice command and LLM call is logged with timing, cost, and token usage (JSONL) |

---

## 🏗️ Architecture

```
Browser (HTML5 Canvas + Socket.IO)
        ↕  WebSocket (state push + events)
Flask + Socket.IO Server (server.py)
        ├── Game Engine       — map, NPCs, entities, resources, combat  (game/)
        ├── Mistral Voxtral   — audio → structured NPC orders           (api/interpreter.py)
        ├── ElevenLabs TTS    — NPC voice line playback                  (api/tts.py)
        └── Pipeline Logger   — structured JSON logs                     (api/logger.py)
```

---

## 🚀 Future Roadmap & Scaling Opportunities

G4AL is just the **foundation** of what's possible with voice-driven AI gaming. The current implementation demonstrates core mechanics, but substantial opportunities remain:

### What We Could Have Done

- **Cloud deployment** (AWS, GCP, Azure) for public hosting and elastic scaling
- **Multi-language support** — extend Voxtral voice recognition beyond English
- **Advanced NPC AI** — dynamic personalities that learn from player interactions and adapt dialogue
- **Procedural storytelling** — AI-generated quests and narrative branches based on voice input
- **Mobile & voice-assistant integration** — play via Alexa, Google Home, or native mobile apps
- **Multiplayer voice coordination** — squads of players commanding shared NPCs via voice chat
- **Emotion & tone detection** — game responds to player sentiment and urgency in speech

### The Vision: Personalized Gaming at Scale

Voice-first AI gaming enables:
- **Adaptive difficulty** based on player communication patterns
- **Persistent NPC memory** — NPCs remember past player decisions and react accordingly
- **Context-aware dialogue generation** — natural, branching conversations unique to each playthrough
- **Real-time collaborative storytelling** — players shaping game narrative through speech

### Deployment Challenges

We intentionally kept the backend local to avoid **prohibitive cloud inference costs**. Hosting a production Voxtral + ElevenLabs pipeline publicly would require:
- Per-user voice processing credits (Mistral API)
- TTS generation fees per NPC line (ElevenLabs)
- Infrastructure overhead (compute, bandwidth, storage)

**This trade-off leaves the door open:** with optimized batching, cached responses, and sponsorship partnerships, a public cloud deployment becomes viable and could unlock this vision for thousands of players.

---

## 📋 Prerequisites

- **Python ≥ 3.11**
- [**uv**](https://docs.astral.sh/uv/) — fast Python package manager
- A **Mistral API key** ([console.mistral.ai](https://console.mistral.ai/))
- (Optional) An **ElevenLabs API key** for NPC voice lines ([elevenlabs.io](https://elevenlabs.io/))

---

## 🚀 Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/Vlor999/G4AL.git
cd G4AL
```

### 2. Install dependencies

```bash
make install
# or directly:
uv sync
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```dotenv
MISTRAL_API_KEY="your-mistral-api-key"
ELEVENLABS_API_KEY="your-elevenlabs-api-key"   # optional
```

### 4. Run the game

```bash
uv run python main.py
```

Then open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

## 🎮 Controls

| Key / Action | Description |
|---|---|
| **WASD** / **Arrow keys** | Move camera |
| **Hold G** | Push-to-talk — record a voice command |
| **Click on NPC** | Select an NPC |

### Example voice commands

> *"Bob, go chop some wood near the forest"*
> *"Paul, build a house next to the storage hut"*
> *"Thomas, plant wheat south of the camp"*
> *"Archers, defend the base!"*

---

## 📁 Project Structure

```
.
├── main.py                 # Entry point
├── server.py               # Flask + Socket.IO backend & game loop
├── Makefile                # install, format, lint commands
├── pyproject.toml          # Dependencies (uv / pip)
├── .env.example            # Environment variable template
│
├── api/                    # AI & voice pipeline
│   ├── interpreter.py      #   Voxtral multimodal → structured NPC orders
│   ├── voice.py            #   Push-to-talk microphone recorder
│   ├── tts.py              #   ElevenLabs text-to-speech engine
│   ├── roster.py           #   NPC profiles (name, personality, voice)
│   ├── characters.py       #   Character soul descriptions
│   └── logger.py           #   Structured pipeline logging (JSONL)
│
├── game/                   # Game engine (headless, no rendering)
│   ├── map.py              #   Procedural tile map generation
│   ├── npc.py              #   NPC & Archer logic, actions, pathfinding
│   ├── entities.py         #   Trees, rocks, structures, wheat fields
│   ├── creatures.py        #   Fauna — sheep, wild archers (enemies)
│   ├── storage.py          #   Resource storage (wood, stone, gold, wheat)
│   └── settings.py         #   Game constants & tuning
│
├── static/                 # Web client (HTML5 Canvas)
│   ├── game.js             #   Main client entry, Socket.IO, camera
│   ├── renderer.js         #   Canvas rendering
│   ├── sprites.js          #   Sprite loading
│   ├── input.js            #   Keyboard & mouse input
│   ├── ptt.js              #   Browser push-to-talk recording
│   ├── ui.js               #   HUD & UI overlays
│   └── assets/             #   Sprite sheets & tilesets
│
└── logs/                   # Pipeline logs (auto-generated)
```

---

## 🔑 API Keys

| Service | Variable | Required | Purpose |
|---|---|---|---|
| **Mistral AI** | `MISTRAL_API_KEY` | ✅ Yes | Voxtral — voice command interpretation |
| **ElevenLabs** | `ELEVENLABS_API_KEY` | ❌ Optional | NPC voice line playback (TTS) |

The game works without ElevenLabs — NPCs will simply not speak aloud.

---

## 📄 License

Built with ❤️ at the **Mistral Worldwide Hackathon 2026**.

## Asset:
Found on [itch.io](https://itch.io/profile/pixelfrog-assets)