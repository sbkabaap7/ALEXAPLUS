"""Shared tool boundary. Private rows are fetched only after authorization."""
import time
from .security import db
from .privacy import evaluate, Decision, privacy_mode

TOOL_META = {
    'get_privacy_state': ('PUBLIC', 'read'),
    'get_public_home_status': ('PUBLIC', 'read'),
    'list_calendar_events': ('PERSONAL', 'read'),
    'list_reminders': ('PERSONAL', 'read'),
    'read_personal_note': ('PERSONAL', 'read'),
    'get_home_device_status': ('PUBLIC', 'read'),
    'create_reminder': ('PERSONAL', 'write'),
    'update_reminder': ('PERSONAL', 'write'),
    'get_access_decision': ('PUBLIC', 'read'),
    'get_privacy_activity_summary': ('PUBLIC', 'read'),
}


def public_state(session):
    return {k: session[k] for k in ('speaker_status', 'guest_presence', 'expires_at', 'similarity')} | {
        'session_id': session['id'][:8], 'mode': privacy_mode(session),
        'authentication_status': 'PIN_VERIFIED' if session['pin_until'] > time.time() else 'UNVERIFIED',
        'pin_until': session['pin_until'], 'candidate_until': session['last_voice_at'] + 120,
    }


def execute(sid: str, name: str, args: dict | None = None):
    args = args or {}
    with db.lock:
        session = db.session(sid)
        if name not in TOOL_META:
            return {'decision': 'DENY', 'reason': 'UNKNOWN_TOOL', 'status': 'denied'}
        sensitivity, operation = TOOL_META[name]
        if name == 'read_personal_note':
            meta = db.one('SELECT sensitivity FROM private_notes WHERE id=?', (args.get('note_id', 1),))
            sensitivity = meta['sensitivity'] if meta else 'SENSITIVE'
        assessment = evaluate(session, sensitivity, operation)
        if assessment.decision != Decision.ALLOW:
            db.audit(session, name, sensitivity, assessment.decision, assessment.reason, 'denied')
            return {'decision': str(assessment.decision), 'reason': assessment.reason, 'status': 'denied'}
        result = None
        if name == 'get_privacy_state':
            result = public_state(session)
        elif name == 'get_public_home_status':
            result = {'household': 'Studio 04 — synthetic demo home', 'quiet_hours': '22:00–07:00', 'time_utc': time.strftime('%H:%M:%S', time.gmtime()), 'source': 'Synthetic stored demo configuration; no live weather service'}
        elif name == 'get_home_device_status':
            result = {'source': 'Synthetic simulator devices; no physical hardware connected', 'microphone': 'User-controlled browser capture only', 'privacy_gateway': 'online'}
        elif name == 'list_calendar_events':
            result = db.all('SELECT * FROM calendar_events ORDER BY starts_at')
        elif name == 'list_reminders':
            result = db.all('SELECT * FROM reminders ORDER BY id')
        elif name == 'read_personal_note':
            result = db.one('SELECT * FROM private_notes WHERE id=?', (args.get('note_id', 1),))
        elif name == 'create_reminder':
            title = args.get('title', '')
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
                return {'decision': 'DENY', 'reason': 'INVALID_INPUT', 'status': 'error'}
            rid = db.execute('INSERT INTO reminders(title) VALUES (?)', (title.strip(),))
            result = {'id': rid, 'created': True}
        elif name == 'update_reminder':
            rid = args.get('reminder_id')
            if type(rid) is not int or type(args.get('completed')) is not bool:
                return {'decision': 'DENY', 'reason': 'INVALID_INPUT', 'status': 'error'}
            if not db.one('SELECT id FROM reminders WHERE id=?', (rid,)):
                return {'decision': 'ALLOW', 'reason': 'NOT_FOUND', 'status': 'error'}
            db.execute('UPDATE reminders SET completed=? WHERE id=?', (int(args['completed']), rid))
            result = {'id': rid, 'updated': True}
        elif name == 'get_access_decision':
            resource = args.get('resource', 'SENSITIVE')
            check = evaluate(session, resource)
            result = {'decision': str(check.decision), 'reason': check.reason, 'resource': resource}
        elif name == 'get_privacy_activity_summary':
            result = db.all('SELECT decision,COUNT(*) AS count FROM privacy_audit_events WHERE session_id=? GROUP BY decision', (sid[:8],))
        db.audit(session, name, sensitivity, assessment.decision, assessment.reason)
        return {'decision': 'ALLOW', 'reason': assessment.reason, 'status': 'completed', 'data': result}
