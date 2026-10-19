from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Annotated, Literal
from .security import current_session
from .tools import execute




def call(name, args=None):
    sid = current_session.get()
    if not sid:
        raise PermissionError('Authenticated application session required')
    return execute(sid, name, args)


def get_privacy_state() -> dict:
    """Read current session privacy, occupancy and independent authentication state."""
    return call('get_privacy_state')


def get_public_home_status() -> dict:
    """Read explicitly public synthetic household information and UTC time."""
    return call('get_public_home_status')


def list_calendar_events() -> dict:
    """Read private synthetic calendar. Backend policy may deny access."""
    return call('list_calendar_events')


def list_reminders() -> dict:
    """Read personal reminders, subject to backend policy."""
    return call('list_reminders')


def read_personal_note(note_id: Annotated[int, Field(ge=1)] = 1) -> dict:
    """Read personal note 1 or sensitive protected record 2, subject to policy."""
    return call('read_personal_note', {'note_id': note_id})


def get_home_device_status() -> dict:
    """Read the simulated device configuration; no physical devices are connected."""
    return call('get_home_device_status')


def create_reminder(title: Annotated[str, Field(min_length=1, max_length=200)]) -> dict:
    """Create a personal reminder only when the server policy permits writes."""
    return call('create_reminder', {'title': title})


def update_reminder(reminder_id: Annotated[int, Field(ge=1)], completed: bool) -> dict:
    """Mark a personal reminder complete or incomplete, subject to policy."""
    return call('update_reminder', {'reminder_id': reminder_id, 'completed': completed})


def get_access_decision(resource: Literal['PUBLIC', 'PERSONAL', 'SENSITIVE'] = 'SENSITIVE') -> dict:
    """Preview policy for a resource classification without reading its contents."""
    return call('get_access_decision', {'resource': resource})


def get_privacy_activity_summary() -> dict:
    """Return decision counts for the authenticated session, without transcripts."""
    return call('get_privacy_activity_summary')


def create_mcp():
    server = FastMCP('GuestGuard AI', stateless_http=True, json_response=True, streamable_http_path='/mcp')
    for function in (get_privacy_state, get_public_home_status, list_calendar_events,
                     list_reminders, read_personal_note, get_home_device_status,
                     create_reminder, update_reminder, get_access_decision,
                     get_privacy_activity_summary):
        server.add_tool(function)
    return server
