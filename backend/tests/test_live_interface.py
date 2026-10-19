import json
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.security import db
from backend.app import streaming


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        client.post('/api/session')
        yield client


def test_capture_start_revokes_private_access_and_keeps_guest_latch(client):
    token = client.cookies['gg_session']
    db.update_session(token, speaker_status='OWNER_CANDIDATE', guest_presence='GUEST_DETECTED',
                      pin_until=time.time()+300, last_voice_at=time.time())
    response = client.post('/api/voice/start')
    assert response.status_code == 200
    state = response.json()
    assert state['authentication_status'] == 'UNVERIFIED'
    assert state['speaker_status'] == 'UNCERTAIN'
    assert state['guest_presence'] == 'GUEST_DETECTED'
    assert client.post('/api/voice/start', headers={'Origin': 'https://example.com'}).status_code == 403


def test_preview_is_authenticated_and_never_grants_identity_or_runs_tools(client, monkeypatch):
    from backend.app import main
    monkeypatch.setattr(main.voice, 'preprocess', lambda raw: ('audio', None, {}))
    monkeypatch.setattr(main, 'transcribe', lambda audio: {'text': 'preview from local audio', 'available': True})
    token = client.cookies['gg_session']
    db.update_session(token, last_voice_at=1)
    result = client.post('/api/voice/preview', files={'audio': ('sample.wav', b'fake test bytes')})
    assert result.json()['text'] == 'preview from local audio'
    assert client.get('/api/state').json()['speaker_status'] == 'UNCERTAIN'
    assert db.session(token)['last_voice_at'] > 1
    assert client.get('/api/history').json() == []
    client.cookies.clear()
    assert client.post('/api/voice/start').status_code == 403
    assert client.post('/api/voice/preview', files={'audio': ('sample.wav', b'fake test bytes')}).status_code == 403


def test_reply_stream_has_real_deltas_and_one_result(client, monkeypatch):
    async def reply(token, text):
        return {'response': 'Tool completed.', 'mode': 'test fixture', 'tool': 'get_public_home_status',
                'result': {'decision': 'ALLOW', 'data': {'test': True}}, 'timeline': [], 'error': False}
    monkeypatch.setattr(streaming, 'run_agent', reply)
    response = client.post('/api/agent/stream', json={'text': 'home'})
    assert response.headers['content-type'].startswith('application/x-ndjson')
    packets = [json.loads(line) for line in response.text.splitlines()]
    assert packets[0]['type'] == 'status'
    assert ''.join(p['text'] for p in packets if p['type'] == 'delta') == 'Tool completed.'
    assert packets[-1]['result']['result']['data'] == {'test': True}
    assert len([p for p in packets if p['type'] == 'result']) == 1
    client.cookies.clear()
    assert client.post('/api/agent/stream', json={'text': 'home'}).status_code == 403


def test_general_answer_streams_model_chunks_without_tool_results(client, monkeypatch):
    async def model_chunks(question):
        assert question == 'Which planet is largest?'
        yield 'Jupi'
        yield 'ter.'
    monkeypatch.setattr(streaming, 'stream_answer', model_chunks)
    packets = [json.loads(line) for line in client.post('/api/agent/stream', json={'text': 'Which planet is largest?'}).text.splitlines()]
    assert [packet['type'] for packet in packets] == ['status', 'delta', 'delta', 'result']
    assert [packet['text'] for packet in packets if packet['type'] == 'delta'] == ['Jupi', 'ter.']
    assert packets[-1]['result']['response'] == 'Jupiter.'
    assert 'tool' not in packets[-1]['result']
    assert db.all('SELECT * FROM privacy_audit_events') == []


def test_private_stream_rechecks_policy_before_delivery(client, monkeypatch):
    async def stale_reply(token, text):
        db.update_session(token, guest_presence='GUEST_DETECTED', pin_until=0)
        return {'response': 'Request permitted.', 'mode': 'test fixture', 'tool': 'read_personal_note',
                'result': {'decision': 'ALLOW', 'data': 'must not leave the server'}, 'timeline': [], 'error': False}
    monkeypatch.setattr(streaming, 'run_agent', stale_reply)
    response = client.post('/api/agent/stream', json={'text': 'note'})
    assert 'must not leave the server' not in response.text
    result = json.loads(response.text.splitlines()[-1])['result']
    assert result['result']['decision'] == 'DENY'
    assert 'data' not in result['result']


def test_authorized_private_answer_is_only_in_final_packet(client, monkeypatch):
    token = client.cookies['gg_session']
    db.update_session(token, speaker_status='OWNER_CANDIDATE', guest_presence='CLEAR',
                      pin_until=time.time()+300, last_voice_at=time.time())
    async def private_reply(token, text):
        return {'response': 'Your demo note says: private test content', 'mode': 'test fixture',
                'tool': 'read_personal_note', 'result': {'decision': 'ALLOW', 'status': 'completed',
                'data': {'body': 'private test content'}}, 'timeline': [], 'error': False}
    monkeypatch.setattr(streaming, 'run_agent', private_reply)
    packets = [json.loads(line) for line in client.post('/api/agent/stream', json={'text': 'note'}).text.splitlines()]
    assert [packet['type'] for packet in packets] == ['status', 'result']
    assert packets[-1]['result']['result']['data']['body'] == 'private test content'
