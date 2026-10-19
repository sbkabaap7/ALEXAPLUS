from backend.app.replies import reply_for


def allowed(data):
    return {'decision': 'ALLOW', 'status': 'completed', 'data': data}


def test_public_and_personal_results_are_concise_answers():
    home = reply_for('get_public_home_status', allowed({'household': 'Studio 04 — synthetic demo home', 'quiet_hours': '22:00–07:00'}))
    assert home == 'The demo home is Studio 04. Quiet hours are 22:00–07:00.'
    calendar = reply_for('list_calendar_events', allowed([{'title': 'Synthetic: design review', 'starts_at': '2026-10-20T10:00:00+05:30'}]))
    assert 'design review — Tue 20 Oct, 10:00 AM' in calendar
    note = reply_for('read_personal_note', allowed({'body': 'Synthetic: birthday surprise at the botanical garden.'}))
    assert note == 'Your demo note says: birthday surprise at the botanical garden.'


def test_denial_never_renders_a_supplied_private_payload():
    denied = {'decision': 'DENY', 'reason': 'GUEST_POLICY_ACTIVE', 'status': 'denied', 'data': {'body': 'private content'}}
    answer = reply_for('read_personal_note', denied)
    assert 'private content' not in answer
    assert 'Ask again using your saved voice' in answer


def test_empty_lists_and_reminder_write_have_useful_replies():
    assert reply_for('list_reminders', allowed([])) == 'You have no demo reminders.'
    assert reply_for('create_reminder', allowed({'created': True})) == 'Done — I added that reminder to this demo.'
