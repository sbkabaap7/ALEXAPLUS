import os
import tempfile
from pathlib import Path

# All test persistence is isolated from the actual owner vault.
os.environ['GUESTGUARD_DATA_DIR'] = tempfile.mkdtemp(prefix='guestguard-tests-')
os.environ['GUESTGUARD_BASE_URL'] = 'http://127.0.0.1:8765'

import pytest
from backend.app.security import db, create_session


@pytest.fixture(autouse=True)
def clean_database():
    with db.connect() as connection:
        for table in ('voice_enrollments', 'sessions', 'privacy_audit_events', 'users'):
            connection.execute(f'DELETE FROM {table}')
    yield


@pytest.fixture
def session_id():
    return create_session()
