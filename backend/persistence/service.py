import hashlib
import json
from datetime import datetime, timezone

from backend.character.models import CharacterProfile, LifeState, LivedExperience, Memory, RelationshipStage
from backend.character.runtime import CharacterRuntime
from backend.life.mira import mira_life_identity, mira_initial_threads
from backend.persistence.store import ConflictError, RuntimeStore, encode


def new_mira(character_id="mira"):
    return CharacterRuntime(
        CharacterProfile(character_id, "Mira", "溫暖、有自己的生活，會留意別人的感受", "自然親近，也尊重對方的空間"),
        life=LifeState(identity=mira_life_identity(), threads=mira_initial_threads()),
    )


def fingerprint(runtime):
    return hashlib.sha256(json.dumps(encode(runtime), ensure_ascii=False,
                                    sort_keys=True).encode()).hexdigest()


def validation_fixture():
    runtime = new_mira("persistence-validation-v1")
    now = datetime(2026, 10, 7, 20, tzinfo=timezone.utc)
    runtime.relationship.stage = RelationshipStage.COMMITTED
    runtime.remember(Memory("記得玩家今天很累，想晚點關心他。", now))
    runtime.mental.unresolved_intentions = ["明天問他睡得好不好"]
    runtime.experience(LivedExperience(
        now, "和 Nina 約好明天吃飯", "傳訊息", "期待", creates_memory=True,
        thread_id="nina-friendship", thread_progress="約好明天見面",
        thread_next_step="明天和 Nina 吃飯", thread_next_step_in_hours=24))
    return runtime


def initialize_database(url):
    # A dedicated fixture never overwrites the actual character. No model calls.
    expected = validation_fixture()
    first = RuntimeStore(url)
    try:
        prior, revision = first.load(expected.profile.id)
        restored_from_previous_process = prior is not None
        if prior is None:
            try:
                first.save(expected, 0)
            except ConflictError:
                pass  # Another startup initialized the same deterministic fixture.
        elif prior != expected:
            raise RuntimeError("Persistence validation snapshot mismatch")
        mira, mira_revision = first.load("mira")
        if mira is None:
            try:
                first.save(new_mira(), 0)
            except ConflictError:
                pass
    finally:
        first.close()
    second = RuntimeStore(url)
    try:
        loaded, revision = second.load(expected.profile.id)
        if loaded != expected:
            raise RuntimeError("Persistence reconnect validation failed")
        mira, mira_revision = second.load("mira")
        if mira is None:
            raise RuntimeError("Missing persistent Mira")
        return {"backend": "postgresql" if url.startswith(("postgres://", "postgresql://")) else "sqlite",
                "fixture_sha256": fingerprint(loaded), "revision": revision,
                "restored_from_previous_process": restored_from_previous_process,
                "mira_revision": mira_revision}
    finally:
        second.close()
