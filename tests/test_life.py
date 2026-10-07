from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json

import pytest
from fastapi.testclient import TestClient

import backend.api as api
from backend.character.models import CharacterProfile, LifeState, LivedExperience
from backend.character.runtime import CharacterRuntime
from backend.life.director import LLMLifeDirector, LIFE_SCHEMA
from backend.life.mira import mira_initial_threads, mira_life_identity

NOW = datetime(2026, 10, 7, 19, tzinfo=timezone.utc)


def runtime():
    return CharacterRuntime(CharacterProfile("mira", "Mira", "warm", "natural"),
                            life=LifeState(identity=mira_life_identity(), threads=mira_initial_threads()))


def event(**changes):
    fields = dict(occurred_at=NOW, summary="Jules and Mira assessed the fictional hawk's flight progress.",
                  activity="Rehab follow-up", emotional_reaction="cautiously pleased", salience=.7,
                  creates_memory=True, thread_id="work-rehab",
                  thread_progress="Hawk still needs flight assessment tomorrow; Jules will observe.",
                  category="career", participants=["Jules"])
    return LivedExperience(**(fields | changes))


class RecordingModel:
    def __init__(self):
        self.calls = []

    def generate_json(self, **kwargs):
        # Payload must remain JSON-compatible after timestamps enter thread state.
        json.dumps(kwargs["payload"])
        self.calls.append(kwargs)
        return {k: v for k, v in asdict(event()).items() if k in LIFE_SCHEMA["properties"]}


def test_director_receives_identity_threads_and_continuity_without_mutation():
    rt = runtime()
    model = RecordingModel()
    director = LLMLifeDirector(model)
    before = asdict(rt)
    result = director.advance(rt, NOW)
    assert asdict(rt) == before
    payload = model.calls[0]["payload"]
    assert payload["life_identity"] == asdict(mira_life_identity())
    assert {t["id"] for t in payload["active_life_threads"]} == {t.id for t in rt.life.threads}
    assert payload["temporal_context"]["local_hour"] == 12
    assert payload["player_present"] is False
    assert payload["world_grounding"] == []
    rt.experience(result)
    director.advance(rt, NOW + timedelta(hours=6))
    second = model.calls[1]["payload"]
    assert second["active_life_threads"][0]["summary"] == result.thread_progress
    assert second["active_life_threads"][0]["last_progress_at"] == NOW.isoformat()
    assert second["recent_memories"][0]["content"] == result.summary
    assert second["mental_state"]["mood"] == result.emotional_reaction
    assert second["temporal_context"]["elapsed_hours"] == 6
    assert second["life_state"]["recent_experiences"][0]["thread_id"] == "work-rehab"


def test_runtime_progresses_only_selected_thread_and_preserves_identity():
    rt = runtime()
    identity = asdict(rt.life.identity)
    other_threads = [asdict(t) for t in rt.life.threads[1:]]
    applied = rt.experience(event())
    assert applied.thread_id == "work-rehab"
    assert rt.life.threads[0].summary == applied.thread_progress
    assert rt.life.threads[0].last_progress_at == NOW
    assert [asdict(t) for t in rt.life.threads[1:]] == other_threads
    assert asdict(rt.life.identity) == identity
    assert rt.memories[0].content == applied.summary


@pytest.mark.parametrize("changes", [
    {"thread_id": "invented"}, {"thread_id": None}, {"thread_progress": None},
    {"thread_progress": "   "}, {"thread_progress": "x" * 2001},
])
def test_invalid_progress_cannot_mutate_threads(changes):
    rt = runtime()
    before = asdict(rt.life)
    applied = rt.experience(event(**changes, future_thread="arbitrary new thread"))
    assert [asdict(t) for t in rt.life.threads] == before["threads"]
    assert applied.thread_id is None and applied.thread_progress is None
    assert rt.life.ongoing_threads == []
    # The independent experience and salient memory are still accepted.
    assert rt.memories[0].content == applied.summary


def test_closed_thread_is_not_offered_or_mutated():
    rt = runtime()
    rt.life.threads[0].status = "closed"
    before = asdict(rt.life.threads[0])
    model = RecordingModel()
    rt.experience(LLMLifeDirector(model).advance(rt, NOW))
    assert "work-rehab" not in {t["id"] for t in model.calls[0]["payload"]["active_life_threads"]}
    assert asdict(rt.life.threads[0]) == before


def test_ordinary_event_does_not_create_memory_and_legacy_bridge_survives():
    rt = CharacterRuntime(CharacterProfile("mira", "Mira", "warm", "natural"))
    rt.experience(event(thread_id=None, thread_progress=None, creates_memory=False, future_thread="A walk tomorrow"))
    assert not rt.memories
    assert rt.life.ongoing_threads == ["A walk tomorrow"]


@pytest.mark.parametrize("method", ["get", "post"])
def test_life_api_runs_28_slices_with_persistent_runtime(monkeypatch, method):
    models = []
    def factory():
        model = RecordingModel()
        models.append(model)
        return model
    monkeypatch.setattr(api, "OpenAIStructuredModel", factory)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "test-commit")
    response = getattr(TestClient(api.app), method)("/experiments/life")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "life-director-v1"
    assert body["commit_sha"] == "test-commit"
    assert body["player_interventions"] == 0
    assert len(body["events"]) == len(models[0].calls) == 28
    assert body["memories_created"] == 28
    assert body["threads_progressed"] == ["work-rehab"]
    assert len(body["threads"]) == 4
    assert body["events"][0]["participants"] == ["Jules"]
    times = [datetime.fromisoformat(e["occurred_at"]) for e in body["events"]]
    assert all(b - a == timedelta(hours=6) for a, b in zip(times, times[1:]))
    assert all(c["payload"]["life_identity"]["profession"] == "wildlife rescue veterinarian" for c in models[0].calls)


def test_pending_checkpoint_persists_and_reaches_next_director_call():
    rt = runtime()
    rt.experience(event(thread_next_step="Review independent feeding with Jules", thread_next_step_in_hours=24))
    assert rt.life.threads[0].next_step == "Review independent feeding with Jules"
    assert rt.life.threads[0].next_check_at == NOW + timedelta(hours=24)
    model = RecordingModel()
    LLMLifeDirector(model).advance(rt, NOW + timedelta(hours=24))
    thread = model.calls[0]["payload"]["active_life_threads"][0]
    assert thread["next_check_at"] == (NOW + timedelta(hours=24)).isoformat()
    # A completed checkpoint can clear its pending plan, without changing thread status.
    rt.experience(event(occurred_at=NOW + timedelta(hours=24)))
    assert rt.life.threads[0].next_step is None
    assert rt.life.threads[0].next_check_at is None
    assert rt.life.threads[0].status == "active"


@pytest.mark.parametrize("hours", [-1, 0, 169, True, "24"])
def test_invalid_checkpoint_does_not_replace_existing_plan(hours):
    rt = runtime()
    rt.experience(event(thread_next_step="Review feeding", thread_next_step_in_hours=24))
    rt.experience(event(thread_next_step="Injected plan", thread_next_step_in_hours=hours))
    assert rt.life.threads[0].next_step == "Review feeding"
    assert rt.life.threads[0].next_check_at == NOW + timedelta(hours=24)


def test_unknown_thread_cannot_install_checkpoint():
    rt = runtime()
    before = [asdict(t) for t in rt.life.threads]
    applied = rt.experience(event(thread_id="invented", thread_next_step="Overwrite life", thread_next_step_in_hours=24))
    assert [asdict(t) for t in rt.life.threads] == before
    assert applied.thread_next_step is None
