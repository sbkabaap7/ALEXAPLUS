"""Pure policy: never accepts a conversational claim as identity evidence."""
from dataclasses import dataclass
from enum import StrEnum
import time


class Decision(StrEnum):
    ALLOW = 'ALLOW'
    REDACT = 'REDACT'
    DENY = 'DENY'
    REQUIRE_VERIFICATION = 'REQUIRE_VERIFICATION'


@dataclass(frozen=True)
class Assessment:
    decision: Decision
    reason: str


def evaluate(session: dict, sensitivity: str, operation: str = 'read', public_writes: bool = False) -> Assessment:
    if session.get('expires_at', 0) <= time.time() or session.get('locked'):
        return Assessment(Decision.DENY, 'SESSION_LOCKED_OR_EXPIRED')
    if sensitivity == 'PUBLIC':
        if operation != 'read' and not public_writes:
            return Assessment(Decision.DENY, 'PUBLIC_WRITE_DISABLED')
        return Assessment(Decision.ALLOW, 'PUBLIC_RESOURCE')
    if sensitivity not in ('PERSONAL', 'SENSITIVE'):
        return Assessment(Decision.DENY, 'UNKNOWN_RESOURCE')
    if session.get('guest_presence') == 'GUEST_DETECTED':
        return Assessment(Decision.DENY, 'GUEST_POLICY_ACTIVE')
    if session.get('speaker_status') != 'OWNER_CANDIDATE':
        return Assessment(Decision.DENY, 'IDENTITY_NOT_ESTABLISHED')
    if session.get('guest_presence') != 'CLEAR':
        return Assessment(Decision.DENY, 'ROOM_STATUS_UNCERTAIN')
    return Assessment(Decision.ALLOW, 'OWNER_VOICE_CLEAR_ROOM')


def voice_transition(session: dict, status: str) -> dict:
    """A fresh owner match opens access; unknown audio restricts until then."""
    if status not in ('OWNER_CANDIDATE', 'UNKNOWN_SPEAKER', 'UNCERTAIN', 'INVALID_AUDIO'):
        raise ValueError('Unsupported speaker status')
    changes = {'speaker_status': status, 'similarity': None}
    if status == 'OWNER_CANDIDATE':
        changes['guest_presence'] = 'CLEAR'
    else:
        changes['pin_until'] = 0
        changes['guest_presence'] = 'GUEST_DETECTED' if status == 'UNKNOWN_SPEAKER' else (
            'GUEST_DETECTED' if session['guest_presence'] == 'GUEST_DETECTED' else 'UNCERTAIN')
    return changes


def privacy_mode(session: dict) -> str:
    if session.get('locked') or session['expires_at'] <= time.time():
        return 'LOCKED'
    if session['guest_presence'] == 'GUEST_DETECTED':
        return 'GUEST'
    if session['guest_presence'] == 'CLEAR' and session['speaker_status'] == 'OWNER_CANDIDATE':
        return 'PRIVATE'
    return 'UNKNOWN'
