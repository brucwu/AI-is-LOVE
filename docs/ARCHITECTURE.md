# AI is LOVE — MVP Architecture

## Architecture strategy

Start as a **modular monolith**. Preserve strong internal boundaries without paying the operational cost of microservices before the behavior is understood.

Major modules:

1. Conversation
2. Character Runtime
3. Memory
4. Deliberation
5. Expression / Model Gateway
6. Background Worker / Scheduler
7. Persistence
8. Simulation / Virtual Clock
9. Proactive Messaging

MCP can later be a standardized boundary to external services, but it should not become the fundamental interface between every internal subsystem.

## MVP delivery platform

The MVP user interface will be a **responsive Web App** rather than a native mobile application.

Deployment target: **Render**.

Initial deployment shape:

- Web frontend: browser-based chat and development/debug UI
- Backend: Python Character Runtime and API
- Background worker: offline deliberation / proactive-message jobs
- PostgreSQL: persistent character, relationship, memory, and conversation state
- Render: hosting/deployment target for the MVP stack

The web client should remain thin: authoritative character state and decisions live on the server. The UI can later evolve into a PWA or native client without replacing the Character Runtime.

## Character Runtime

The Character Runtime is the authoritative persistent representation of a character.

It owns or coordinates:

- CharacterProfile / CharacterCore
- RelationshipState
- MentalState
- structured Memory
- unresolved intentions
- temporal state
- deliberation history
- conversation context selection
- validated state transitions

It is explicitly **not** an LLM instance.

## Model abstraction

Cloud model APIs sit behind a model abstraction layer.

The runtime supplies selected context. A model may propose:

- a deliberation result
- memory candidates
- mental-state changes
- relationship-state changes
- an outward intent
- player-visible expression

The runtime validates and applies allowed changes. Model output never directly becomes authoritative persistent state.

## Suggested domain schemas

### CharacterProfile

Relatively stable character identity and behavior constraints.

Possible fields:

- id
- name
- background
- personality
- values
- attachment_style
- expression_style
- preferences
- romantic_orientation_toward_player
- version

### RelationshipState

Possible fields:

- character_id
- player_id
- relationship_stage
- trust
- intimacy
- longing
- hurt
- security
- updated_at

### MentalState

Possible fields:

- character_id
- mood
- active_thoughts
- desires
- unresolved_intentions
- emotional_residue
- last_deliberated_at
- next_wakeup_at

### Memory

Possible fields:

- id
- character_id
- player_id
- type
- content
- occurred_at
- recorded_at
- importance
- emotional_weight
- relationship_relevance
- retrieval_tags

### DeliberationResult

Possible fields:

- character_id
- timestamp
- trigger
- selected_context
- internal_summary
- proposed_state_updates
- decision: ACT | WAIT
- intent
- reason
- next_wakeup_hint

## Conversation flow

1. Player sends a message.
2. Conversation module records the raw message.
3. Character Runtime retrieves relevant Character Core, Relationship State, Mental State, memories, and recent conversation.
4. Model performs cognition/deliberation.
5. Runtime validates proposed state and memory updates.
6. If a response is appropriate, expression step generates character-consistent wording.
7. Runtime records resulting state, memories, and conversation output.

## Offline/background flow

1. Scheduler wakes the character because a deliberation opportunity is due.
2. Runtime loads persistent state.
3. Relevant memories, time context, unresolved intentions, and relationship context are selected.
4. Deliberation model returns structured reasoning/result.
5. Runtime validates state changes.
6. Decision is explicitly ACT or WAIT.
7. WAIT: persist any legitimate internal changes/intention and schedule another opportunity.
8. ACT: pass the chosen intent to expression.
9. If the action is a proactive message, persist it and eventually dispatch through push/messaging infrastructure.

A wakeup is not equivalent to an action.

## Scheduler philosophy

Avoid fixed routines such as "message every morning" as the fundamental mechanic.

The scheduler answers:

> When should this character get another opportunity to think?

The character/runtime answers:

> Given everything I know and feel now, do I actually want to do anything?

Wakeup timing can later use a mixture of:

- elapsed time
- unresolved intention urgency
- anticipated events
- relationship state
- recent interaction intensity
- stochastic jitter
- model-suggested revisit time

## Persistence

For production, PostgreSQL is a reasonable target for structured state, memories, jobs, and conversation metadata.

For the first simulation, persistence may be simplified as long as the domain interfaces do not assume in-memory state is permanent.

## Background jobs and push

Production will eventually need:

- durable scheduled jobs
- worker execution
- idempotency
- retry policy
- push notification / message dispatch
- observability

These should follow behavioral validation, not precede it.

## Simulation-first architecture

Before building the full client, implement a virtual clock.

The simulator should be able to:

- advance time rapidly
- wake the character according to scheduler decisions
- inject player interactions/events
- log retrieved context
- log deliberation outputs
- log ACT/WAIT
- log state transitions
- log proactive messages
- replay deterministic scenarios where practical

This provides a fast way to answer the most important MVP question: **does the character feel like a persistent person rather than a scheduled chatbot?**

## Proposed repository structure

```text
backend/
  character/
  memory/
  deliberation/
  models/
  simulation/
    virtual_clock/
tests/
docs/
  DESIGN.md
  ARCHITECTURE.md
  MVP_ROADMAP.md
.env.example
README.md
pyproject.toml
```

This is a logical boundary proposal; directories should be created when code needs them rather than as empty scaffolding.
