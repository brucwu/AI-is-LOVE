from datetime import datetime, timezone
import pytest
from backend.character.models import CharacterProfile, Memory, LivedExperience, RelationshipStage
from backend.character.runtime import CharacterRuntime
from backend.life.mira import mira_life_identity, mira_initial_threads
from backend.persistence.store import RuntimeStore, ConflictError


def test_restart_preserves_full_runtime_and_chinese_checkpoints(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'runtime.db')
    runtime = CharacterRuntime(CharacterProfile('mira', 'Mira', '溫暖', '自然'))
    runtime.life.identity = mira_life_identity()
    runtime.life.threads = mira_initial_threads()
    runtime.relationship.stage = RelationshipStage.COMMITTED
    runtime.mental.unresolved_intentions = ['想問他今天過得怎麼樣']
    now = datetime.now(timezone.utc)
    runtime.experience(LivedExperience(now, '和 Nina 約好吃飯', '傳訊息', '期待',
        creates_memory=True, thread_id='nina-friendship', thread_progress='約好明天見面',
        thread_next_step='明天和 Nina 吃飯', thread_next_step_in_hours=24))
    first = RuntimeStore(url)
    assert first.save(runtime, 0) == 1
    first.close()
    second = RuntimeStore(url)
    restored, revision = second.load('mira')
    assert revision == 1
    assert restored == runtime
    assert isinstance(restored.memories[0].occurred_at, datetime)
    assert restored.relationship.stage is RelationshipStage.COMMITTED
    restored.remember(Memory('照片完成了', now))
    assert second.save(restored, revision) == 2
    second.close()
    third = RuntimeStore(url)
    assert third.load('mira')[0].memories[-1].content == '照片完成了'
    third.close()


def test_stale_writers_cannot_overwrite_and_missing_character_is_not_created(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'runtime.db')
    a, b = RuntimeStore(url), RuntimeStore(url)
    assert a.load('absent') == (None, 0)
    runtime = CharacterRuntime(CharacterProfile('mira', 'Mira', '溫暖', '自然'))
    a.save(runtime, 0)
    stale, revision = b.load('mira')
    runtime.mental.mood = '開心'
    a.save(runtime, 1)
    stale.mental.mood = '疲倦'
    with pytest.raises(ConflictError):
        b.save(stale, revision)
    with pytest.raises(ConflictError):
        b.save(stale, 0)
    assert a.load('mira')[0].mental.mood == '開心'
    a.close()
    b.close()
