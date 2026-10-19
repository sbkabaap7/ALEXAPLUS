import io
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.security import db


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        client.post('/api/session')
        yield client


def test_session_pin_room_and_tampering(client):
    assert client.get('/api/state').json()['mode'] == 'UNKNOWN'
    assert client.post('/api/guest/clear', json={'confirmed': True}).status_code == 403
    assert client.post('/api/pin/setup', json={'pin': '845276'}).status_code == 200
    assert client.post('/api/guest/clear', json={'confirmed': True, 'role': 'owner'}).status_code == 422
    assert client.post('/api/guest/clear', json={'confirmed': False}).status_code == 400
    assert client.post('/api/guest/clear', json={'confirmed': True}).json()['guest_presence'] == 'CLEAR'
    assert client.post('/api/guest/simulate', json={'state': 'GUEST_DETECTED'}).json()['authentication_status'] == 'UNVERIFIED'
    assert client.post('/api/pin/verify', json={'pin': '845276'}).status_code == 200
    assert client.get('/api/state').json()['guest_presence'] == 'GUEST_DETECTED'
    assert client.post('/api/guest/simulate', json={'state': 'CLEAR'}).status_code == 422
    assert client.post('/api/session', headers={'Origin': 'https://evil.example'}).status_code == 403


def test_pin_rate_limit_across_sessions(client):
    client.post('/api/pin/setup', json={'pin': '845276'})
    for _ in range(5):
        assert client.post('/api/pin/verify', json={'pin': '000000'}).status_code == 403
        client.post('/api/session')
    assert client.post('/api/pin/verify', json={'pin': '845276'}).status_code == 403
    assert db.one('SELECT blocked_until FROM users')['blocked_until'] > time.time()


def test_audio_errors_and_enrollment_deletion(client):
    client.post('/api/pin/setup', json={'pin': '845276'})
    result = client.post('/api/voice', files={'audio': ('invalid.wav', b'not audio', 'audio/wav')})
    assert result.status_code == 400
    assert client.get('/api/state').json()['authentication_status'] == 'UNVERIFIED'
    assert client.delete('/api/identity').status_code == 403
    client.post('/api/pin/verify', json={'pin': '845276'})
    assert client.delete('/api/identity').json()['deleted'] is True
    assert client.get('/api/identity').json()['enrolled'] is False
    assert client.post('/api/identity/enroll', data={'consent': 'false'}, files=[('samples', ('a.wav', b'invalid'))]*3).status_code == 403


def test_retention_configuration_and_reset(client):
    assert client.put('/api/rules', json={'audit_days': 2}).status_code == 403
    client.post('/api/pin/setup', json={'pin': '845276'})
    assert client.put('/api/rules', json={'audit_days': 0}).status_code == 422
    assert client.put('/api/rules', json={'audit_days': 2, 'allow_guests': True}).status_code == 422
    assert client.put('/api/rules', json={'audit_days': 2}).status_code == 200
    assert client.get('/api/rules').json()['settings']['audit_days'] == 2
    assert client.delete('/api/history').status_code == 200
    assert client.post('/api/data/reset', json={'confirmed': True}).status_code == 200
    assert not db.one('SELECT * FROM users')
    assert not db.one('SELECT * FROM sessions')
