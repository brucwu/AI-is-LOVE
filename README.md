# AI is LOVE

An AI romance game focused on making the player feel that they met a person who thinks about them, pursues them, and develops a persistent relationship with them — not that they configured an ideal chatbot.

## MVP

The first MVP is intentionally narrow:

- One player
- One persistent AI character
- Chat-first interaction
- Character state persists while the app is closed
- The character can deliberate independently and decide whether to act
- The character may proactively message the player
- "Do nothing / wait" is a valid character decision
- Development begins with an accelerated-time simulation before a full client

## Core principles

> Time creates opportunities for thought, not behavior.

A scheduler may wake the character, but it must not mechanically cause a message or scripted behavior.

> LLM thinks; Runtime remembers; Character decides; LLM expresses.

The AI character is not an LLM session. The persistent Character Runtime owns identity, relationship state, memory, mental state, unresolved intentions, and validated state transitions. Models are replaceable components used for cognition and expression.

## Documents

- [Product & Character Design](docs/DESIGN.md)
- [MVP Architecture](docs/ARCHITECTURE.md)
- [MVP Roadmap](docs/MVP_ROADMAP.md)

## First engineering milestone

Build one test character and run an accelerated virtual-clock simulation over several in-world days. Log every wakeup, deliberation, ACT/WAIT decision, state transition, and proactive-message decision. Use the simulation to tune character continuity and autonomy before committing to the full app stack.
