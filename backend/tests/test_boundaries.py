import asyncio
import time
from pathlib import Path
import numpy as np
import pytest
import httpx
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.security import db, create_session, verify_pin, passwords
from backend.app.tools import execute
from backend.app.database import Database
from backend.app import voice


def test_database_persists_and_audit_omits_private_content(session_id):
    db.update_session(session_id, speaker_status='OWNER_CANDIDATE', guest_presence='CLEAR', pin_until=0, last_voice_at=time.time())
    output = execute(session_id, 'read_personal_note', {'note_id': 2})
    assert output['decision'] == 'ALLOW'
    assert db.session(session_id)['pin_until'] == 0
    assert Database(db.path).session(session_id)['guest_presence'] == 'CLEAR'
    assert 'confidential record' not in str(db.all('SELECT * FROM privacy_audit_events'))
    db.update_session(session_id, guest_presence='GUEST_DETECTED')
    assert execute(session_id, 'read_personal_note', {'note_id': 2})['decision'] == 'DENY'


def test_candidate_evidence_expires_independently(session_id):
    db.update_session(session_id, speaker_status='OWNER_CANDIDATE', guest_presence='CLEAR', pin_until=time.time()+30, last_voice_at=time.time()-121)
    assert execute(session_id, 'list_calendar_events')['decision'] == 'DENY'
    assert db.session(session_id)['pin_until'] == 0


def test_enrollment_requires_consent_and_three_samples():
    with TestClient(create_app()) as client:
        client.post('/api/session')
        client.post('/api/pin/setup', json={'pin': '845276'})
        files = [('samples', ('sample.wav', b'invalid', 'audio/wav'))]*3
        assert client.post('/api/identity/enroll', data={'consent': 'false'}, files=files).status_code == 400
        assert client.post('/api/identity/enroll', data={'consent': 'true'}, files=files[:2]).status_code == 400
        assert not db.one('SELECT * FROM voice_enrollments')


async def test_late_inference_cannot_restore_deleted_enrollment(monkeypatch):
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
        await client.post('/api/session')
        token = client.cookies.get('gg_session')
        def slow_verify(raw):
            time.sleep(.15)
            return np.zeros(16000), {'speaker_status': 'OWNER_CANDIDATE', 'similarity': .99, 'quality': {}}
        monkeypatch.setattr(voice, 'verify', slow_verify)
        task = asyncio.create_task(client.post('/api/voice', files={'audio': ('sample.wav', b'placeholder', 'audio/wav')}))
        await asyncio.sleep(.05)
        # Same invalidation applied by actual enrollment deletion/rotation.
        db.update_session(token, speaker_status='UNCERTAIN', pin_until=0, last_voice_at=0)
        response = await task
        assert response.status_code == 400
        assert db.session(token)['speaker_status'] == 'UNCERTAIN'


async def test_disconnected_mcp_never_reports_success(session_id, monkeypatch):
    from backend.app.agent import run_agent
    from backend.app.config import settings
    monkeypatch.setattr(settings, 'base_url', 'http://127.0.0.1:1')
    output = await run_agent(session_id, 'Read my calendar')
    assert output['error']
    assert 'result' not in output
    assert output['timeline'][-1]['stage'] == 'connection/error'
