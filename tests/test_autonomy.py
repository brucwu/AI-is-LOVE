from datetime import datetime, timedelta, timezone
from backend.autonomy.loop import tick
from backend.character.models import LivedExperience, Decision, DeliberationResult
from backend.persistence.service import initialize_database
from backend.persistence.store import RuntimeStore

NOW = datetime(2026, 10, 8, 4, tzinfo=timezone.utc)


class Director:
    calls = 0
    def advance(self, runtime, now):
        self.calls += 1
        return LivedExperience(now, "和 Nina 約好週末散步", "約時間", "期待",
                               creates_memory=True, thread_id="nina-friendship",
                               thread_progress="週末和 Nina 散步")


class Deliberator:
    calls = 0
    def deliberate(self, runtime):
        self.calls += 1
        return DeliberationResult(Decision.WAIT, "想她，但現在先讓她休息。", next_wakeup_minutes=60)


def setup(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'life.db')
    initialize_database(url)
    return url, Director(), Deliberator()


def test_restart_retains_wait_memory_due_time_and_no_duplicate_calls(tmp_path):
    url, life, mind = setup(tmp_path)
    a = tick(url, NOW, life, mind, jitter=lambda a,b: 0)
    assert a['decision'] == 'WAIT' and a['delivery'] == 'none'
    store = RuntimeStore(url)
    runtime, revision = store.load('mira'); store.close()
    assert runtime.memories[-1].content == '和 Nina 約好週末散步'
    assert runtime.autonomy.attempts_today == 1
    assert tick(url, NOW, life, mind)['status'] == 'waiting'
    assert life.calls == mind.calls == 1
    b = tick(url, NOW+timedelta(hours=1), life, mind, jitter=lambda a,b: 0)
    assert not b['life_advanced'] and mind.calls == 2 and life.calls == 1


def test_budget_and_sleep_do_not_replay_missed_days(tmp_path):
    url, life, mind = setup(tmp_path)
    tick(url, NOW, life, mind, daily_limit=1, jitter=lambda a,b: 0)
    assert tick(url, NOW+timedelta(hours=1), life, mind, daily_limit=1)['status']=='budget_wait'
    assert tick(url, NOW+timedelta(days=3), life, mind, daily_limit=1)['status']=='advanced'
    assert life.calls == 2 and mind.calls == 2


def test_error_reservation_survives_restart(tmp_path):
    import pytest
    url, life, mind = setup(tmp_path)
    def broken(runtime, now): raise RuntimeError('provider unavailable')
    life.advance = broken
    with pytest.raises(RuntimeError): tick(url, NOW, life, mind)
    assert tick(url, NOW+timedelta(minutes=1), life, mind)['status']=='waiting'
    store=RuntimeStore(url); r,_=store.load('mira');store.close()
    assert r.autonomy.attempts_today==1 and not r.life.recent_experiences


def test_manual_write_during_generation_is_not_overwritten(tmp_path):
    url, life, mind=setup(tmp_path)
    def concurrent(runtime):
        store=RuntimeStore(url); other,rev=store.load('mira')
        other.mental.mood='玩家剛說了重要的事';store.save(other,rev);store.close()
        return DeliberationResult(Decision.ACT,'想關心他','問他今天還好嗎',60)
    mind.deliberate=concurrent
    assert tick(url,NOW,life,mind)['status']=='conflict'
    store=RuntimeStore(url);r,_=store.load('mira');store.close()
    assert r.mental.mood=='玩家剛說了重要的事' and not r.life.recent_experiences


def test_act_is_persisted_but_never_sent(tmp_path):
    url, life, mind = setup(tmp_path)
    mind.deliberate=lambda r: DeliberationResult(Decision.ACT,'想問他今天如何','今天還好嗎',75)
    out=tick(url,NOW,life,mind,jitter=lambda a,b: 0)
    assert out['decision']=='ACT' and out['delivery']=='none'
    store=RuntimeStore(url);r,_=store.load('mira');store.close()
    assert r.autonomy.proposed_intent=='今天還好嗎'


def test_reserved_opportunity_blocks_second_process(tmp_path):
    url, life, mind=setup(tmp_path)
    original=life.advance
    def nested(runtime, now):
        assert tick(url,now,Director(),Deliberator())['status']=='waiting'
        return original(runtime,now)
    life.advance=nested
    assert tick(url,NOW,life,mind)['status']=='advanced'
    assert life.calls==1


def test_old_snapshot_without_autonomy_restores_default(tmp_path):
    import json
    url, _, _=setup(tmp_path)
    store=RuntimeStore(url)
    row=store.connection.execute("SELECT payload FROM character_snapshots WHERE character_id='mira'").fetchone()
    document=json.loads(row[0]);document['runtime'].pop('autonomy')
    with store.transaction():
        store.connection.execute("UPDATE character_snapshots SET payload=? WHERE character_id='mira'",(json.dumps(document),))
    r,_=store.load('mira');store.close()
    assert r.autonomy.next_wakeup_at is None and r.autonomy.attempts_today==0


def test_cognition_receives_life_local_time_and_unsent_intent(tmp_path):
    from backend.deliberation.llm import LLMDeliberator
    url,life,mind=setup(tmp_path)
    tick(url,NOW,life,mind)
    store=RuntimeStore(url);r,_=store.load('mira');store.close()
    class Model:
        def generate_json(self, **kwargs):
            p=kwargs['payload']
            assert p['life_context']['recent_experiences'][-1]['summary']=='和 Nina 約好週末散步'
            assert p['temporal_context']['local_now'].endswith('-07:00')
            assert p['previous_internal_decision']['delivered'] is False
            return dict(decision='WAIT',reason='她那邊已經很晚了',intent=None,next_wakeup_minutes=180)
    assert LLMDeliberator(Model()).deliberate(r).decision==Decision.WAIT


def test_act_publishes_once_and_survives_restart(tmp_path):
    url, life, mind = setup(tmp_path)
    mind.deliberate = lambda r: DeliberationResult(Decision.ACT, '想分享', '分享散步', 60)
    class Composer:
        calls = 0
        def proactive(self, runtime, now, intent):
            self.calls += 1
            assert intent == '分享散步'
            return '剛和 Nina 約好散步，也想起你了。'
    composer = Composer()
    out = tick(url, NOW, life, mind, composer=composer, jitter=lambda a,b: 0)
    assert out['delivery'] == 'inbox'
    assert tick(url, NOW, life, mind, composer=composer)['status'] == 'waiting'
    store = RuntimeStore(url); r, _ = store.load('mira'); store.close()
    assert len(r.conversation) == 1 and composer.calls == 1
    assert r.conversation[0].origin == 'mira' and r.conversation[0].player_text == ''
    assert r.conversation[0].id == r.autonomy.last_delivery_id
    assert r.conversation[0].reply == '剛和 Nina 約好散步，也想起你了。'


def test_wait_never_calls_proactive_composer(tmp_path):
    url, life, mind = setup(tmp_path)
    class Composer:
        def proactive(self, *args):
            raise AssertionError('WAIT must not send')
    assert tick(url, NOW, life, mind, composer=Composer())['delivery'] == 'none'


def test_proactive_concurrent_player_update_discards_stale_message(tmp_path):
    url, life, mind = setup(tmp_path)
    mind.deliberate = lambda r: DeliberationResult(Decision.ACT, '想分享', '分享散步', 60)
    class Composer:
        def proactive(self, *args):
            store = RuntimeStore(url); r, rev = store.load('mira')
            r.mental.mood = '玩家剛聯絡'; store.save(r, rev); store.close()
            return '舊訊息'
    assert tick(url, NOW, life, mind, composer=Composer())['status'] == 'conflict'
    store = RuntimeStore(url); r, _ = store.load('mira'); store.close()
    assert r.mental.mood == '玩家剛聯絡' and not r.conversation
