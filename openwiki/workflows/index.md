# Files

- [Game loop and state push](game-loop-and-state-push.md) - How GameEngine advances the simulation at 60 FPS under one lock, in what order a frame updates the world, and how the state is serialised and pushed over Socket.IO every third tick.
- [Voice and typed order flow](voice-order-flow.md) - The path of a spoken or typed command from the browser to an NPC action and a spoken reply, including every point where the command can be refused or dropped.
