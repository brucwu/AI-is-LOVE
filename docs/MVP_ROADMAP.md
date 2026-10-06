# AI is LOVE — MVP Roadmap

## Milestone 0 — Living specification

Goal: keep product principles and architecture decisions in the repository as the source of truth.

Deliverables:

- product/character design
- MVP architecture
- explicit MVP scope
- domain schemas
- behavioral principles

## Milestone 1 — Character simulation

Build the smallest executable Character Runtime and virtual-clock simulator.

One test character is enough.

Implement:

- CharacterProfile
- RelationshipState
- MentalState
- Memory
- DeliberationResult
- virtual clock
- wakeup scheduling
- structured ACT/WAIT deliberation
- persistent unresolved intentions
- simulation logs

Run accelerated scenarios covering roughly 3–7 in-world days.

Questions to answer:

- Does the character think too often?
- Does it message too often?
- Does WAIT happen naturally?
- Do prior interactions meaningfully affect later thoughts?
- Do intentions survive across time?
- Does the character feel continuous rather than reset?
- Does proactive behavior feel motivated rather than scheduled?

## Milestone 2 — Chat loop

Add the minimum player conversation path.

Implement:

- player message ingestion
- recent conversation history
- memory retrieval
- context assembly
- response deliberation
- expression generation
- validated state/memory updates

The same Character Runtime must serve both chat and offline deliberation.

## Milestone 3 — Background execution and proactive messages

Move virtual behavior toward real elapsed time.

Implement:

- durable jobs
- background worker
- idempotent character wakeups
- proactive-message persistence
- notification/message dispatch
- retry/error handling
- basic observability

## Milestone 4 — Client experience

Build the minimal **responsive Web App** experience around the validated runtime and deploy the MVP on **Render**.

Focus on:

- natural conversation
- incoming proactive messages
- relationship continuity
- clear notification behavior
- fast resume from offline state
- responsive desktop/mobile browser layout
- Render deployment and environment configuration
- development/debug view for simulation and character state

## Milestone 5 — Character generation

After the core experience works, explore generating a character rather than asking the player to configure an ideal partner.

Generation should produce a coherent Character Core with enough independence and imperfection to support the feeling of meeting someone.

## Engineering priorities

1. Behavioral correctness before infrastructure complexity.
2. Simulation before polished UI.
3. Persistent state before prompt tricks.
4. Explicit decisions before generated expression.
5. Replaceable model APIs.
6. Tests around state transitions and autonomy.
7. GitHub documents remain living specifications as implementation evolves.

## Immediate implementation target

Create a Python simulation skeleton with:

- domain models
- Character Runtime
- deliberation interface
- deterministic fake deliberator for tests
- virtual clock
- scheduler
- event log
- first pytest scenarios

Only after that baseline behaves correctly should the project choose or deepen production model APIs, database integration, jobs, and production web stack.
