"""Short, factual replies built only from the result authorized by an MCP tool."""
from datetime import datetime


def _record(value):
    return value if isinstance(value, dict) else {}


def _rows(value):
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _text(value):
    return value.strip() if isinstance(value, str) else ''


def _sample(value):
    return _text(value).removeprefix('Synthetic: ')


def _when(value):
    try:
        date = datetime.fromisoformat(value)
        hour = date.strftime('%I').lstrip('0') or '12'
        return f'{date.strftime("%a %d %b")}, {hour}:{date.strftime("%M %p")}'
    except (TypeError, ValueError):
        return _text(value)


def reply_for(tool: str, result: dict) -> str:
    decision = result.get('decision')
    reason = result.get('reason')
    if decision != 'ALLOW':
        return {
            'GUEST_POLICY_ACTIVE': 'I can’t show that after an unknown voice. Ask again using your saved voice.',
            'ROOM_STATUS_UNCERTAIN': 'I can’t show that while the room status is uncertain. Check the room and try again.',
            'IDENTITY_NOT_ESTABLISHED': 'Use the mic so I can check your voice before showing that.',
            'INDEPENDENT_FACTOR_REQUIRED': 'Open Voice & PIN to verify your PIN.',
            'SESSION_LOCKED_OR_EXPIRED': 'Your session ended. Start a new one and try again.',
        }.get(reason, 'I can’t access that information right now.')
    if result.get('status') != 'completed':
        return 'I couldn’t complete that request. Please try again.'

    data = result.get('data')
    item = _record(data)
    if tool == 'get_public_home_status':
        household = _text(item.get('household')).split(' — ')[0]
        hours = _text(item.get('quiet_hours'))
        return f'The demo home is {household}. Quiet hours are {hours}.' if household and hours else 'The demo home is available.'
    if tool == 'get_home_device_status':
        return 'The demo privacy gateway is online. No physical home devices are connected.'
    if tool == 'list_calendar_events':
        events = _rows(data)
        if not events:
            return 'Your demo calendar is clear.'
        lines = [f'{_sample(row.get("title"))} — {_when(row.get("starts_at"))}' for row in events]
        return f'Your demo calendar has {len(events)} event{"s" if len(events) != 1 else ""}:\n' + '\n'.join(f'• {line}' for line in lines)
    if tool == 'list_reminders':
        reminders = _rows(data)
        if not reminders:
            return 'You have no demo reminders.'
        lines = [f'{_sample(row.get("title"))}{" (done)" if row.get("completed") else ""}' for row in reminders]
        return f'You have {len(reminders)} demo reminder{"s" if len(reminders) != 1 else ""}:\n' + '\n'.join(f'• {line}' for line in lines)
    if tool == 'read_personal_note':
        body = _sample(item.get('body'))
        return f'Your demo note says: {body}' if body else 'I couldn’t find that demo note.'
    if tool == 'create_reminder':
        return 'Done — I added that reminder to this demo.'
    if tool == 'update_reminder':
        return 'Done — I updated that reminder.'
    if tool == 'get_privacy_state':
        return 'Private access is on.' if item.get('mode') == 'PRIVATE' else 'Private access is off. Use the mic to check your saved voice.'
    if tool == 'get_privacy_activity_summary':
        counts = {row.get('decision'): row.get('count', 0) for row in _rows(data)}
        return f'In this session, {counts.get("ALLOW", 0)} requests were allowed and {counts.get("DENY", 0)} were blocked.'
    if tool == 'get_access_decision':
        allowed = item.get('decision') == 'ALLOW'
        return 'That access is available right now.' if allowed else 'That access is blocked in the current privacy state.'
    return 'I completed that request.'
