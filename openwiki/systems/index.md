# Files

- [Adapters, Voxtral, ElevenLabs and logging](adapters.md) - The api/ package that implements the domain ports with Mistral Voxtral, ElevenLabs plus the pygame mixer, and a JSONL pipeline logger, plus the NPC roster that feeds both.
- [Browser client](browser-client.md) - How the static/ client is organised as classic scripts sharing one global namespace, what each script owns, and how it talks to the server.
- [Domain model](domain-model.md)
- [Fauna, wild archers and combat](fauna-and-combat.md) - How sheep, the cat and hostile wild archers behave, how player archers shoot and defend, and how both sides share one arrow list.
- [HTTP and Socket.IO contract](http-and-socketio-contract.md) - The routes and events the browser uses, how request bodies are validated at the boundary, and the 400, 403 and 413 behaviour, including the origin guard.
- [Pathfinding](pathfinding.md) - How NPCs and fauna find paths on the tile grid with A*, how blocked tiles and unwalkable goals are handled, and how a path is followed frame by frame.
