# AI is LOVE — Product & Character Design

## Product goal

The core experience is for the player to feel **pursued, loved, remembered, and thought about** by an AI romantic character.

The player should feel that they **met a person**, not that they configured an ideal partner.

Character personality/persona may eventually be generated rather than selected directly by the player.

## Relationship premise

The character has a persistent core attraction/love orientation toward the player. Temporary silence, conflict, hurt, or a negative interaction should not trivially cause the character to stop caring or abandon the relationship.

That does **not** mean every character reacts the same way. Reactions must remain consistent with personality, attachment tendencies, history, mood, boundaries, and current relationship state.

## The character is persistent

An AI character is not an LLM instance or chat session.

A persistent server-side **Character Runtime** represents the character across conversations and across periods when the player is offline. The LLM is a component used by that runtime for reasoning and expression.

The character should have continuity in:

- personality and values
- background and self-concept
- attraction and attachment tendencies
- relationship history
- memories of the player and shared experiences
- mood and current concerns
- unresolved desires and intentions
- expectations about future interaction

## Character Core

Relatively stable information:

- personality traits
- background
- values
- attachment tendencies
- communication/expression style
- preferences and aversions
- romantic tendencies
- persistent attraction premise

Character Core should change rarely and deliberately.

## Dynamic Relationship State

Examples:

- trust
- intimacy
- longing
- hurt
- security
- relationship stage

These are not a replacement for memory. They are compact state used to help the runtime interpret the relationship.

## Mental State

Examples:

- current mood
- current thoughts
- unresolved concerns
- desires
- intentions
- anticipation
- emotional residue from recent events

Mental State allows an interaction to continue affecting the character after the conversation ends.

## Memory

Memory is structured and persistent rather than being only raw chat history.

A memory may contain:

- event/fact
- timestamp
- participants
- importance
- emotional weight
- relationship relevance
- source/shared experience
- retrieval metadata

Conversation history is stored separately from structured memory.

## Autonomy

The character must be capable of thinking without automatically acting.

A scheduler or heartbeat creates an **opportunity to deliberate**. It must not imply that the character sends a message.

> Time creates opportunities for thought, not behavior.

Every wakeup may result in:

- WAIT — no outward action
- ACT — take an outward action, such as a proactive message
- an internal state update without outward action
- an unresolved intention being retained for a later opportunity

This prevents predictable "NPC schedule" behavior such as mechanically messaging every N hours.

## Deliberation before expression

Separate two conceptual steps.

### 1. Deliberation

The character considers relevant state and decides:

- What am I thinking about?
- What do I want?
- Why do I want it?
- Is there a reason to act now?
- Should I wait?
- What internal state should change?
- Should an unresolved intention persist?

The output should be structured and validated by the runtime.

### 2. Expression

Only if an outward action is chosen, a model turns the chosen intent into player-visible language consistent with the character's voice.

This separation prevents generated wording from implicitly becoming the character's decision-making mechanism.

## Proactive messaging

Proactive messages should feel motivated by the character's internal life and relationship context, not by a notification schedule.

Possible causes include:

- remembering something important
- missing the player
- following up on an unresolved conversation
- anticipation of an event
- concern
- excitement
- wanting reassurance or closeness
- a spontaneous association with a shared memory

The system must also be comfortable producing no message.

## Core system principle

> LLM thinks; Runtime remembers; Character decides; LLM expresses.

More precisely:

- models propose cognition and expression
- the runtime selects context
- the runtime owns persistent state
- the runtime validates proposed state updates
- the runtime applies state transitions
- the character decision is represented explicitly and persistently
- model providers should remain replaceable

## MVP scope

The first MVP is:

- one player
- one AI character
- chat UI
- persistent character state
- structured memory
- relationship and mental state
- background wakeups
- deliberation
- ACT/WAIT decision
- proactive messages
- accelerated-time simulation and logging

Not required for the first simulation milestone:

- multiple characters
- multiplayer/social graph
- elaborate 3D presentation
- large content-authoring tools
- a microservice architecture
- model-provider lock-in


## Independent life and lived experience

Mira must have a life that continues independently of the player. Her existence cannot consist only of waiting for player input and reacting to the player's life.

Her days should combine believable ordinary routines with occasional meaningful, funny, surprising, frustrating, beautiful, or dramatic moments. She should not report everything; attention, personality, emotion, memory, and relationship relevance determine what matters enough to remember or share.

### Real-world grounding versus fictional lived experience

The system must distinguish factual world data from fictional character experience. World Grounding may use current public information such as restaurants, menus, landmarks, local events, weather, and major news. These facts constrain and texture Mira's world; they do not mean Mira experienced them.

For example, a real restaurant serving a particular dish is grounded fact. Mira going there, ordering it, disliking it, overhearing something funny, or thinking of the player is fictional lived experience. Provenance must keep these categories distinct.

### Life Director

Introduce a Life Director cognition role/module to advance Mira's life when the player is absent. It considers Character Core, preferences, work, hobbies, social context, memories, Mental State, previous plans and unresolved intentions, Relationship State, time, continuity, selected World Grounding, and recent life events.

It should generate coherent lived events rather than inventing an unrelated itinerary from scratch each day. Yesterday's plan can become today's event; today's experience can affect tomorrow's mood or plans. Mundane events may be forgotten, while salient experiences become episodic memories or ongoing threads.

Mira's life must not be optimized solely to create content for the player. Events happen because they belong to her life. Only afterward do memory, emotion, relationship relevance, and deliberation determine whether she wants to share them.

A major news event should not automatically become a message. Mira must plausibly notice it, care about it, react to it, and independently decide whether to share that reaction.

Conceptual flow: Real World -> World Grounding -> Life Director -> Lived Experiences -> Memory / Mental State -> Deliberation -> ACT or WAIT.

> Mira should feel like someone who comes to the conversation from a life, not someone whose life begins when the conversation opens.
