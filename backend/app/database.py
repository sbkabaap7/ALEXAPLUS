"""Small, parameterized SQLite repository with safe versioned initialization."""
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY CHECK(id=1), pin_hash TEXT NOT NULL, attempts INTEGER DEFAULT 0, blocked_until REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, mcp_hash TEXT UNIQUE NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL, speaker_status TEXT NOT NULL DEFAULT 'UNCERTAIN', guest_presence TEXT NOT NULL DEFAULT 'UNCERTAIN', pin_until REAL DEFAULT 0, locked INTEGER DEFAULT 0, similarity REAL, last_voice_at REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS guest_presence (session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE, state TEXT NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS voice_enrollments (id INTEGER PRIMARY KEY CHECK(id=1), template BLOB NOT NULL, sample_count INTEGER NOT NULL, consent_at REAL NOT NULL, model TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS voice_template_metadata (enrollment_id INTEGER PRIMARY KEY REFERENCES voice_enrollments(id) ON DELETE CASCADE, dimensions INTEGER NOT NULL, threshold REAL NOT NULL);
CREATE TABLE IF NOT EXISTS privacy_rules (id INTEGER PRIMARY KEY CHECK(id=1), audit_days INTEGER NOT NULL DEFAULT 7, public_reminders INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS calendar_events (id INTEGER PRIMARY KEY, title TEXT NOT NULL, starts_at TEXT NOT NULL, sensitivity TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, title TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, sensitivity TEXT NOT NULL DEFAULT 'PERSONAL');
CREATE TABLE IF NOT EXISTS private_notes (id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, sensitivity TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS privacy_audit_events (id INTEGER PRIMARY KEY, timestamp REAL NOT NULL, session_id TEXT NOT NULL, speaker_status TEXT NOT NULL, guest_presence TEXT NOT NULL, tool TEXT NOT NULL, sensitivity TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT NOT NULL, result_status TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS audit_time_idx ON privacy_audit_events(timestamp);
PRAGMA user_version=1;
'''


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        with self.connect() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] > 1:
                raise ValueError('Database schema is newer than this application. Refusing downgrade.')
            db.executescript(SCHEMA)
            db.execute('INSERT OR IGNORE INTO privacy_rules(id) VALUES (1)')
            if not db.execute('SELECT id FROM calendar_events LIMIT 1').fetchone():
                db.executemany('INSERT INTO calendar_events VALUES (?,?,?,?)', [
                    (1, 'Synthetic: design review', '2026-10-20T10:00:00+05:30', 'PERSONAL'),
                    (2, 'Community garden opening', '2026-10-21T09:00:00+05:30', 'PUBLIC')])
                db.execute("INSERT INTO reminders(title) VALUES ('Synthetic: collect library books')")
                db.executemany('INSERT INTO private_notes VALUES (?,?,?,?)', [
                    (1, 'Personal note', 'Synthetic: birthday surprise at the botanical garden.', 'PERSONAL'),
                    (2, 'Protected record', 'Synthetic confidential record: demonstration data only.', 'SENSITIVE')])

    @contextmanager
    def connect(self):
        with self.lock:
            db = sqlite3.connect(self.path, timeout=15)
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()

    def one(self, sql, args=()):
        with self.connect() as db:
            row = db.execute(sql, args).fetchone()
            return dict(row) if row else None

    def all(self, sql, args=()):
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, args).fetchall()]

    def execute(self, sql, args=()):
        with self.connect() as db:
            return db.execute(sql, args).lastrowid

    def session(self, sid):
        row = self.one('SELECT * FROM sessions WHERE id=?', (sid,))
        if not row or row['expires_at'] <= time.time() or row['locked']:
            raise PermissionError('Session unavailable. Start a new session.')
        # Candidate evidence is short-lived independently of PIN/session expiry.
        if row['speaker_status'] == 'OWNER_CANDIDATE' and row['last_voice_at'] < time.time() - 120:
            self.update_session(sid, speaker_status='UNCERTAIN', pin_until=0)
            row.update(speaker_status='UNCERTAIN', pin_until=0)
        return row

    def update_session(self, sid, **fields):
        allowed = {'speaker_status', 'guest_presence', 'pin_until', 'locked', 'similarity', 'last_voice_at'}
        if not fields or not set(fields) <= allowed:
            raise ValueError('Invalid session fields')
        with self.connect() as db:
            db.execute(f"UPDATE sessions SET {','.join(k+'=?' for k in fields)} WHERE id=?", (*fields.values(), sid))
            if 'guest_presence' in fields:
                db.execute('INSERT OR REPLACE INTO guest_presence VALUES (?,?,?)', (sid, fields['guest_presence'], time.time()))

    def audit(self, session, tool, sensitivity, decision, reason, status='completed'):
        days = self.one('SELECT audit_days FROM privacy_rules WHERE id=1')['audit_days']
        with self.connect() as db:
            db.execute('DELETE FROM privacy_audit_events WHERE timestamp<?', (time.time()-days*86400,))
            db.execute('INSERT INTO privacy_audit_events(timestamp,session_id,speaker_status,guest_presence,tool,sensitivity,decision,reason,result_status) VALUES (?,?,?,?,?,?,?,?,?)',
                (time.time(), session['id'][:8], session['speaker_status'], session['guest_presence'], tool, sensitivity, str(decision), reason, status))
