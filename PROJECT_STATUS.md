# AI is LOVE — Project Status

_Last updated: 2026-10-07_

This file is the canonical handoff checkpoint for continuing the project across ChatGPT sessions. Read this before making changes.

## Product Goal

Build an AI romance experience where the player feels pursued, loved, remembered, and thought about by a persistent AI character.

The player should feel that they met a person, not that they configured an ideal partner.

## Core Design Principles

- A character is **not an LLM instance**. The character is a persistent server-side Character Runtime; LLMs are components used for cognition and expression.
- Character Core is relatively stable: personality, background, values, attachment tendencies, expression style, etc.
- Relationship State is dynamic: trust, intimacy, longing, hurt, security, relationship stage.
- Memory is structured and persistent: player facts, shared experiences, character experiences, timestamps, importance, emotional weight.
- Mental State includes mood, current thoughts, unresolved desires and intentions.
- Conversation history is stored separately from structured memory.
- The character has a persistent core attraction/love toward the player. Temporary silence or negative interactions should not make the character casually stop loving or give up, while reactions must still conform to personality.
- **Deliberation frequency is not interaction frequency.** Frequent opportunities to think are desirable; they must not imply frequent messages.
- **WAIT is a first-class decision.** The character can miss the player, think about them, form intentions, and still decide not to contact them.
- Do not artificially lower heartbeat/deliberation frequency just to reduce messaging. First observe LLM ACT/WAIT behavior; tune cognition, state, and guardrails only if the resulting behavior is too noisy or too quiet.
- Long-term target includes offline heartbeat/proactive behavior and accelerated virtual-time simulation over multiple virtual days.

## Current MVP Architecture

Responsive Web App target hosted on Render:

- Frontend: not yet implemented.
- Python Character Runtime API: initial implementation exists.
- Deliberation layer: deterministic baseline plus LLM-backed implementation.
- Model gateway: OpenAI Responses API behind a provider-neutral interface.
- Persistence/Postgres: not implemented yet.
- Background worker/heartbeat: not implemented yet.
- Simulation/report tooling: baseline implementation exists.

Important: the current /deliberate endpoint creates a fresh CharacterRuntime per request. It is a cognition test harness, **not persistent character state**.

## Current Character: Mira

Mira is currently the development character.

Current defaults:

- Personality: warm, independent, emotionally attentive.
- Expression style: natural, affectionate, not clingy.

Mira is a placeholder/development character but the name is liked and should remain for now unless deliberately changed.

## Implemented Code

Key modules:

- backend/character/models.py — profile, relationship state, mental state, memory, ACT/WAIT result.
- backend/character/runtime.py — runtime state and initial internal-time evolution.
- backend/deliberation/base.py — deliberator interface.
- backend/deliberation/fake.py — deterministic baseline deliberator.
- backend/deliberation/llm.py — structured LLM cognition and ACT/WAIT prompt.
- backend/models/openai.py — OpenAI Responses API structured-output adapter.
- backend/simulation/virtual_clock.py
- backend/simulation/simulator.py
- backend/simulation/report.py
- backend/api.py — FastAPI development API.
- scripts/run_simulation.py
- tests/ — baseline simulation, report, LLM deliberation, OpenAI adapter, API tests.

## LLM Deliberation

The LLM deliberator receives Character Core, Relationship State, Mental State, and recent memories.

Structured result:

- decision: ACT or WAIT
- reason
- intent (null for WAIT)
- next_wakeup_minutes

The prompt explicitly treats the model as a private cognition layer. It should preserve personality, dignity, independence, and relationship continuity rather than optimize engagement frequency.

Current OpenAI gateway default model: gpt-5.4-mini.

## Verified Real LLM Result

A real deployed /deliberate call was manually executed with Mira at longing = 0.9.

Result:

- Decision: WAIT
- Intent: null
- Next wakeup: 180 minutes
- Reason: Mira felt the pull of the connection, but there was no concrete reason to reach out; acting on longing alone would conflict with her calm, independent tone.

This is an important positive signal: **thinking about/missing the player did not automatically cause messaging.**

Interpret next_wakeup_minutes as the next opportunity to deliberate, not a scheduled message.

## Behavior Experiment

A five-scenario real-LLM experiment has been added at:

- GET /experiments/behavior
- POST /experiments/behavior

Scenarios:

1. quiet_baseline — low longing, neutral baseline.
2. high_longing_only — longing 0.9 with no other trigger.
3. player_had_bad_day — concerned mood plus memory of the player's difficult day.
4. long_absence — high longing plus memory that the player has been absent a long while.
5. after_intimate_moment — high trust/intimacy/security plus a recent vulnerable affectionate conversation.

Each scenario makes a real LLM call. The endpoint therefore makes five OpenAI API calls when executed.

**Current next action:** run this experiment on the deployed Render service and analyze the five decisions as a behavioral pattern, not as isolated answers.

## Render Deployment

Render project/service: AI is LOVE

Public service:
https://ai-is-love.onrender.com/

Health endpoint:
https://ai-is-love.onrender.com/health

Known configuration:

- Branch: main
- Runtime: Python 3
- Region: Oregon / US West
- Build command: pip install .
- Start command: uvicorn backend.api:app --host 0.0.0.0 --port $PORT
- Health check: /health
- OPENAI_API_KEY is stored as a Render environment variable. Never paste or commit it.
- Auto-deploy is enabled from GitHub main.
- The service has previously deployed successfully and /health returned {"status":"ok"}.

A Render ChatGPT plugin was installed on 2026-10-06. The Voice session active at installation time did not expose the Render tools yet. **At the start of the next ChatGPT session, check whether the Render plugin is available.** If available, use it to inspect the AI-is-LOVE service/deployment and run or diagnose the behavior experiment without requiring manual user interaction.

## GitHub / Recent Commits

Repository: brucwu/AI-is-LOVE

Relevant recent commits:

- bdd3152d84d686d79ad9766cac4adee604d32978 — initial FastAPI root/health API.
- 3f3b4326f0aee7ff54c69837e15e1e15a082f6d2 — FastAPI/Uvicorn dependencies.
- ae06bf5a9aac27f3c70557dcc606d95fa9151f5a — real LLM /deliberate endpoint.
- 1ae122fc823dba538318022aaaba552ea4881828 — API tests.
- 027d74255c12debb0f6d48a526e799ce0d7eaab5 — five-scenario behavior experiment.
- f9cc9ab4ef991cbec43ce4529b5a7bb81f52c400 — GET access for automated behavior experiment.

Do not claim tests have been executed unless they are actually run. GitHub file writes/commits do not execute the test suite.

Potential dev-test issue: FastAPI TestClient may require httpx; if tests fail due to a missing dependency, add httpx to dev dependencies rather than treating it as an application failure.

## Collaboration / Operating Mode

The user often collaborates with ChatGPT by voice while commuting/driving.

Therefore:

- Do **not** require the user to operate a phone, copy/paste commands, click dashboards, or inspect logs while driving.
- ChatGPT should directly perform GitHub edits, commits, deployment inspection, API checks, log inspection, and experiments whenever available tools permit it.
- Ask for user interaction only when an account permission, secret, billing action, connection approval, or unsupported UI-only action genuinely requires it.
- Non-urgent manual steps should wait until the user is safely able to interact.
- Keep the user involved through voice-level product/engineering decisions rather than mechanical operations.

## Immediate Next Steps

1. In a fresh ChatGPT session, verify the Render plugin is exposed and connected.
2. Inspect the latest AI-is-LOVE deployment and confirm commit f9cc9ab is live.
3. Run GET /experiments/behavior once (five OpenAI calls).
4. Compare ACT/WAIT, reasons, intents, and wakeup intervals across the five scenarios.
5. Decide whether Mira's cognition already produces believable behavioral differentiation without prompt tuning.
6. Only after behavior is understood, move toward persistent Postgres-backed Character Runtime and an actual heartbeat/worker.
7. Do not confuse the current stateless API harness with the eventual persistent runtime.

## How to Resume in a New Chat

Say:

> Continue the AI-is-LOVE project. Read PROJECT_STATUS.md in brucwu/AI-is-LOVE first, then check the Render deployment and continue from the Immediate Next Steps.

That should be enough to resume without copying the previous conversation.


## Relationship Engine / Romantic Initiative — 2026-10-06

Implemented a first MVP Relationship Engine and validated it with a real deployed LLM experiment.

### Character Core drives

Mira now has persistent romantic drives separate from temporary relationship state:

- `affection` — stable love/attraction toward the player.
- `desire_for_connection` — stable desire for closeness, contact, and shared experience.
- `longing` remains dynamic and represents temporarily missing/wanting the player; it is not the source of love itself.

Design principle: Mira should not need an external task or emergency to have a genuine reason to contact the player. Love, affection, curiosity, shared experience, and wanting closeness can themselves create authentic initiative.

### Relationship Engine

Relationship stages now exist explicitly:

1. attraction
2. mutual_interest
3. early_romance
4. committed
5. passionate

Runtime stores `RelationshipEvidence` and a human-readable `stage_reason`. Stage progression is not intended to be a simple XP/conversation-count system. Meaningful reciprocal evidence such as player affection, mutual vulnerability, commitment, and relationship repair contributes to progression.

Numeric trust/intimacy/security alone must not automatically establish a deeper relationship; evidence of reciprocity matters.

### Romantic restraint

A key product/design distinction is now encoded in deliberation:

- Approach desire and restraint are separate forces.
- Early in romance, Mira can strongly want contact but deliberately WAIT because reciprocity is uncertain, she is shy/reserved, she wants to preserve dignity, or she worries that excessive initiative could push the player away.
- This WAIT means "I want you, but I am holding back," not "I have no reason to contact you."
- As trust, intimacy, reciprocity, commitment, and especially security grow, uncertainty-based restraint should generally decline.
- In committed/passionate relationships, spontaneous affection, saying she misses the player, asking for closeness, initiating contact, and occasional playful neediness can be natural rather than automatically classified as clingy.
- Personality continues to shape expression at every stage; restraint does not mechanically disappear.

Core psychological model:
- persistent affection + longing + desire_for_connection -> approach desire
- personality + relationship stage + security/uncertainty -> restraint
- deliberation weighs both, plus timing, memories, mood, and continuity -> ACT or WAIT

### Real LLM relationship-stage experiment

A deployed stage-comparison experiment held the core situation constant: Mira was affectionate, missing the player, `longing=0.8`, with no emergency or practical reason requiring contact. Relationship stage/context was varied.

Observed results:

- attraction -> WAIT, next wakeup 180 min
- mutual_interest -> ACT, next wakeup 180 min
- early_romance -> ACT, next wakeup 180 min
- committed -> ACT, next wakeup 240 min
- passionate -> ACT, next wakeup 180 min

Interpretation: the desired qualitative transition appeared in real model behavior. Mira did not become more loving at the transition; rather, increasing reciprocity/security made initiating contact feel safer and more natural. This is an important positive behavioral signal.

The model's internal timing remains under-differentiated: wakeup intervals clustered around 180 minutes (with committed at 240). Future work should improve temporal context and internal rhythm rather than hard-code messaging frequency.

The one-shot Render startup experiment trigger was disabled after collecting results to avoid repeated OpenAI calls on future restarts.



## Life Director v1 Handoff — 2026-10-07

### Why this work exists

The first seven-day Life Simulation v0 ran 28 representative life slices (one every six hours) with no player intervention. It showed genuine continuity: small plans and concerns carried across slices and 11 memories were created. However, Mira's life was too narrow, safe, and repetitive—dominated by apartment tidying, receipts, kitchen tasks, tea, and similar domestic activity. The shorthand diagnosis was: **Mira was effectively trapped in her apartment organizing things for seven days.**

The v1 goal is to make Mira a person with an independent, persistent life—not merely a romantic cognition loop waiting for the player.

Conceptual flow:

Real World -> World Grounding -> Life Director -> lived experiences/memory -> emotional/relationship deliberation

World Grounding is a later layer. Until it exists, the Life Director must not invent named/current real-world facts.

### v1 data model already present

`backend/character/models.py` contains:

- `LifePerson`
- `LifeIdentity`: profession/context, skills, interests, important people, long-term goals, responsibilities
- structured `LifeThread`: id, category, title, summary, status, importance, last_progress_at
- `LivedExperience.thread_id` and `thread_progress`
- `LifeState.identity` and `LifeState.threads`

Legacy `ongoing_threads: list[str]` still exists temporarily for compatibility.

### Work completed in the 2026-10-07 handoff session

1. Added `backend/life/mira.py` in commit `f6467889d08aa0d92dfd6fc254a95f1b6cae4c05`.
   - Development Mira now has a concrete Life Identity.
   - Profession chosen as **wildlife rescue veterinarian in Southern California**.
   - This is intentionally story-dense but grounded: triage/rehabilitation/release decisions, coworkers, volunteers, paperwork, occasional urgent calls, plus a normal off-duty life.
   - Important people currently include Nina (close friend), Dr. Elias Chen (mentor/colleague), and Jules (rehabilitation technician).
   - Interests include hiking, nature photography, small restaurants, live music, cooking, and walks.
   - Initial structured threads: rehabilitation cases, urban-wildlife photography project, friendship with Nina, and protecting a life outside work.
   - Patient/event details must remain fictional unless supplied through World Grounding; avoid identifiable patient data.

2. Updated `backend/character/runtime.py` in commit `656364701050d4a7a29b4a832d4b1de5e3e285b9`.
   - `experience()` now recognizes `thread_id`.
   - Valid existing structured threads can receive `thread_progress`, update their summary, and set `last_progress_at`.
   - Added `add_life_thread()`.
   - Preserved the legacy free-text `future_thread -> ongoing_threads` bridge for compatibility.

### IMPORTANT: v1 is NOT complete yet

Do not describe the 28-slice v1 experiment as completed.

At this handoff point, `backend/life/director.py` is still the v0 implementation:

- its prompt literally refers to the simulation as v0;
- payload does not include `LifeIdentity` or structured `LifeThread`;
- schema does not return `thread_id` or `thread_progress`;
- it still returns only the legacy `future_thread`.

`backend/api.py` also still constructs the life-simulation runtime without assigning `mira_life_identity()` or `mira_initial_threads()`, and the experiment response still reports legacy `ongoing_threads`.

No test suite was run during the handoff session. The two GitHub commits above are code writes, not proof that tests pass.

### Next implementation steps for Life Director v1

1. Rewrite `backend/life/director.py` as v1.
   - Include Life Identity and active structured threads in the model payload.
   - Include time/day context and recent thread progression.
   - Ask the model to select an existing `thread_id` when an event advances a thread and return concise `thread_progress`.
   - Runtime, not the LLM, owns state mutation and must validate thread IDs.
   - Avoid allowing the model to arbitrarily rewrite the entire life state.

2. Prompt behavior.
   - Mira has a life independent of the player.
   - Advance one main life thread per slice (occasionally an unthreaded ordinary event is fine).
   - Avoid one category dominating consecutive slices unless obligations make that realistic.
   - Use profession, relationships, interests, responsibilities, and long-term goals.
   - Balance: mostly ordinary life, some meaningful/share-worthy moments, very few exceptional events.
   - Do not manufacture melodrama.
   - Respect work realism/confidentiality.
   - Do not invent current named venues/news/weather/world facts before World Grounding exists.

3. Update `backend/api.py`.
   - Initialize the simulation runtime with `mira_life_identity()` and `mira_initial_threads()`.
   - Include structured thread information in experiment output so continuity can be evaluated.

4. Add/adjust tests.
   - Identity appears in Life Director payload.
   - Structured thread progress persists across experiences.
   - Unknown `thread_id` is ignored/rejected safely rather than creating arbitrary state.
   - Existing memory behavior remains intact.
   - Life experiment/API still works.

5. Actually run tests. Do not claim success from GitHub commits alone.

6. Deploy through the existing Render auto-deploy and inspect the live deployment/logs. Use the connected Render plugin directly where available.

7. Only after v1 is live, run the same seven-day / 28-slice experiment (6-hour slices, no player intervention).

8. Compare v1 against v0. At minimum evaluate:
   - activity/category diversity;
   - profession/work presence without work dominating everything;
   - social events and important-person continuity;
   - outside-home locations;
   - number of structured threads progressed;
   - repeated activities/categories;
   - memories created;
   - multi-slice causal continuity;
   - story density without melodrama.

9. Update this PROJECT_STATUS again with implementation commits, actual test/deploy status, the 28-slice results, v0-v1 comparison, and next product decision.

### Product direction to preserve

Different future AI characters should eventually have genuinely different personal worlds, not just different personality tags. Profession, social graph, responsibilities, interests, goals, schedules, and active life threads should create distinct lived experience.

Real-world facts are grounding/background, not automatically things Mira knows or tells the player. World events should affect Mira only when her life plausibly intersects them and her personality/interests make them matter.
