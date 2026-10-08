from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
import backend.api as api
from backend.chat.service import ChatComposer, ChatBusy, RequestMismatch, send_message
from backend.persistence.service import initialize_database
from backend.persistence.store import RuntimeStore
from backend.deliberation.llm import LLMDeliberator

NOW = datetime(2026, 10, 8, 4, tzinfo=timezone.utc)


class Composer:
    calls = 0
    def reply(self, runtime, now):
        self.calls += 1
        assert runtime.life.identity.profession
        assert runtime.conversation[-1].player_text == '你好，Mira'
        return '嗨，很高興你來找我。'


@pytest.fixture
def url(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'chat.db')
    initialize_database(url)
    return url


def test_restart_and_duplicate_id_have_one_saved_reply(url):
    c = Composer()
    result = send_message(url, 'request-1', '你好，Mira', c, NOW)
    assert send_message(url, 'request-1', '你好，Mira', c, NOW) == result
    assert c.calls == 1
    initialize_database(url)
    s = RuntimeStore(url)
    runtime, _ = s.load('mira')
    s.close()
    assert len(runtime.conversation) == 1
    assert runtime.conversation[0].reply == result['reply']
    assert runtime.life.identity.profession
    with pytest.raises(RequestMismatch):
        send_message(url, 'request-1', '另一則訊息', c, NOW)


def test_provider_failure_preserves_input_for_retry(url):
    class Broken:
        def reply(self, runtime, now):
            raise RuntimeError('provider failure')
    with pytest.raises(RuntimeError):
        send_message(url, 'request-1', '你好，Mira', Broken(), NOW)
    result = send_message(url, 'request-1', '你好，Mira', Composer(), NOW)
    assert result['reply']


def test_new_message_cannot_pass_unanswered_turn_and_overlap(url):
    class Overlap(Composer):
        def reply(self, runtime, now):
            with pytest.raises(ChatBusy):
                send_message(url, 'request-1', '你好，Mira', Composer(), NOW)
            with pytest.raises(ChatBusy):
                send_message(url, 'request-2', '別的訊息', Composer(), NOW)
            return super().reply(runtime, now)
    send_message(url, 'request-1', '你好，Mira', Overlap(), NOW)


def test_chat_reply_merges_concurrent_life_state(url):
    class Concurrent(Composer):
        def reply(self, runtime, now):
            store = RuntimeStore(url)
            newer, revision = store.load('mira')
            newer.life.current_activity = '下班散步'
            store.save(newer, revision)
            store.close()
            return super().reply(runtime, now)
    send_message(url, 'request-1', '你好，Mira', Concurrent(), NOW)
    store = RuntimeStore(url)
    runtime, _ = store.load('mira')
    store.close()
    assert runtime.life.current_activity == '下班散步'
    assert runtime.conversation[-1].reply


def test_crashed_reservation_recovers_and_old_owner_cannot_write(url):
    class Replaced(Composer):
        def reply(self, runtime, now):
            send_message(url, 'request-1', '你好，Mira', Composer(), NOW + timedelta(minutes=4))
            return '舊程序的回覆'
    result = send_message(url, 'request-1', '你好，Mira', Replaced(), NOW)
    assert result['reply'] == '嗨，很高興你來找我。'


def test_composer_and_cognition_receive_chinese_conversation(url):
    send_message(url, 'request-1', '你好，Mira', Composer(), NOW)
    s = RuntimeStore(url)
    runtime, _ = s.load('mira')
    s.close()
    class Model:
        def generate_json(self, **kwargs):
            p = kwargs['payload']
            if kwargs.get('schema_name') == 'chat_reply':
                assert p['conversation'][-1]['mira'] == '嗨，很高興你來找我。'
                assert p['identity']['profession']
                return {'reply': '今天過得如何？'}
            assert p['recent_conversation'][-1]['player'] == '你好，Mira'
            return {'decision': 'WAIT', 'reason': '剛聊過。', 'intent': None, 'next_wakeup_minutes': 90}
    assert ChatComposer(Model()).reply(runtime, NOW) == '今天過得如何？'
    assert LLMDeliberator(Model()).deliberate(runtime).reason == '剛聊過。'


def test_api_auth_input_history_and_safe_error(url, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('CHAT_ACCESS_TOKEN', 'test-only')
    monkeypatch.setenv('RUNTIME_API_TOKEN', 'admin-only')
    monkeypatch.delenv('AUTONOMY_ENABLED', raising=False)
    monkeypatch.setattr(api, 'chat_composer', lambda: Composer())
    h = {'Authorization': 'Bearer test-only'}
    with TestClient(api.app) as client:
        page = client.get('/')
        assert 'text/html' in page.headers['content-type']
        assert 'textContent' in page.text
        assert 'localStorage' not in page.text
        assert client.get('/chat').status_code == 401
        assert client.get('/runtime/mira', headers=h).status_code == 401
        assert client.get('/chat', headers={'Authorization': 'Bearer admin-only'}).status_code == 401
        assert client.post('/chat', json={'request_id': 'request-1', 'text': '你好，Mira'}).status_code == 401
        assert client.post('/chat', headers=h, json={'request_id': 'bad', 'text': 'x'}).status_code == 422
        assert client.post('/chat', headers=h, json={'request_id': 'request-1', 'text': '   '}).status_code == 422
        body = {'request_id': 'request-1', 'text': '你好，Mira'}
        assert client.post('/chat', headers=h, json=body).status_code == 200
        history = client.get('/chat', headers=h).json()
        assert len(history['turns']) == 1
        assert 'owner' not in history['turns'][0]
        assert 'relationship' not in history
    with TestClient(api.app) as client:
        assert client.get('/chat', headers=h).json() == history
        class Broken:
            def reply(self, runtime, now):
                raise RuntimeError('sensitive-provider-details')
        monkeypatch.setattr(api, 'chat_composer', lambda: Broken())
        r = client.post('/chat', headers=h, json={'request_id': 'request-2', 'text': 'hi'})
        assert r.status_code == 502
        assert 'sensitive' not in r.text
