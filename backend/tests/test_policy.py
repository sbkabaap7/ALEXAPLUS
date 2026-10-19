import itertools
import time
import pytest
from backend.app.privacy import evaluate, voice_transition, privacy_mode


@pytest.mark.parametrize('speaker,guest,pin,sensitivity', list(itertools.product(
    ['OWNER_CANDIDATE', 'UNKNOWN_SPEAKER', 'UNCERTAIN', 'INVALID_AUDIO'],
    ['CLEAR', 'GUEST_DETECTED', 'UNCERTAIN'], [True, False], ['PUBLIC', 'PERSONAL', 'SENSITIVE'])))
def test_complete_policy_matrix(speaker, guest, pin, sensitivity):
    session = {'speaker_status': speaker, 'guest_presence': guest, 'pin_until': time.time()+30 if pin else 0, 'expires_at': time.time()+30}
    result = evaluate(session, sensitivity)
    if sensitivity == 'PUBLIC':
        assert result.decision == 'ALLOW'
    elif guest != 'CLEAR' or speaker != 'OWNER_CANDIDATE':
        assert result.decision == 'DENY'
    else:
        assert result.decision == 'ALLOW'
        assert result.reason == 'OWNER_VOICE_CLEAR_ROOM'


@pytest.mark.parametrize('initial', ['CLEAR', 'UNCERTAIN', 'GUEST_DETECTED'])
@pytest.mark.parametrize('status', ['OWNER_CANDIDATE', 'UNKNOWN_SPEAKER', 'UNCERTAIN', 'INVALID_AUDIO'])
def test_voice_transitions(initial, status):
    session = {'guest_presence': initial, 'pin_until': time.time()+30}
    changes = voice_transition(session, status)
    if status == 'OWNER_CANDIDATE':
        assert changes['guest_presence'] == 'CLEAR'
    else:
        assert changes['pin_until'] == 0
        assert changes['guest_presence'] != 'CLEAR'
    if initial == 'GUEST_DETECTED' and status != 'OWNER_CANDIDATE':
        assert changes.get('guest_presence', initial) == 'GUEST_DETECTED'


def test_expired_locked_unknown_resource():
    for session in ({'expires_at': 0}, {'expires_at': time.time()+30, 'locked': True}):
        assert evaluate(session, 'PUBLIC').decision == 'DENY'
        assert privacy_mode(session) == 'LOCKED'
    assert evaluate({'expires_at': time.time()+30}, 'MADE_UP').decision == 'DENY'


def test_saved_voice_opens_private_mode_without_pin_until_candidate_expires():
    session = {'speaker_status': 'OWNER_CANDIDATE', 'guest_presence': 'CLEAR',
               'pin_until': 0, 'expires_at': time.time()+60}
    assert privacy_mode(session) == 'PRIVATE'
    assert evaluate(session, 'PERSONAL').decision == 'ALLOW'
    assert evaluate(session, 'SENSITIVE').decision == 'ALLOW'
    session['guest_presence'] = 'GUEST_DETECTED'
    assert privacy_mode(session) == 'GUEST'
    assert evaluate(session, 'SENSITIVE').decision == 'DENY'
    session.update(voice_transition(session, 'OWNER_CANDIDATE'))
    assert privacy_mode(session) == 'PRIVATE'
    assert evaluate(session, 'SENSITIVE').decision == 'ALLOW'
