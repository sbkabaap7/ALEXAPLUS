import hashlib
import hmac
import secrets
import time
from contextvars import ContextVar
from cryptography.fernet import Fernet
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from .config import settings
from .database import Database

db = Database(settings.data_dir / 'guestguard.sqlite3')
settings.data_dir.mkdir(parents=True, exist_ok=True)
key_path = settings.data_dir / 'template.key'
if not key_path.exists():
    try:
        with key_path.open('xb') as file:
            file.write(Fernet.generate_key())
        key_path.chmod(0o600)
    except FileExistsError:
        pass
key = key_path.read_bytes()
cipher = Fernet(key)
passwords = PasswordHasher()
current_session: ContextVar[str] = ContextVar('guestguard_session', default='')


def mcp_token(sid: str) -> str:
    return hmac.new(key, ('mcp:'+sid).encode(), hashlib.sha256).hexdigest()


def create_session():
    sid = secrets.token_urlsafe(32)
    now = time.time()
    db.execute('DELETE FROM sessions WHERE expires_at<?', (now,))
    db.execute('INSERT INTO sessions(id,mcp_hash,created_at,expires_at) VALUES (?,?,?,?)',
               (sid, hashlib.sha256(mcp_token(sid).encode()).hexdigest(), now, now+settings.session_seconds))
    db.update_session(sid, guest_presence='UNCERTAIN')
    return sid


def verify_pin(sid: str, pin: str):
    db.session(sid)
    # A repository lock serializes attempts across sessions and concurrent requests.
    with db.lock:
        user = db.one('SELECT * FROM users WHERE id=1')
        if not user:
            raise ValueError('Set an owner PIN in Settings first.')
        if user['blocked_until'] > time.time():
            raise PermissionError('PIN temporarily locked. Try again in five minutes.')
        valid = False
        try:
            valid = passwords.verify(user['pin_hash'], pin)
        except (VerifyMismatchError, VerificationError):
            pass
        if not valid:
            attempts = user['attempts']+1
            db.execute('UPDATE users SET attempts=?,blocked_until=? WHERE id=1',
                       (attempts, time.time()+300 if attempts >= 5 else 0))
            db.update_session(sid, pin_until=0)
            raise PermissionError('PIN verification failed.')
        db.execute('UPDATE users SET attempts=0,blocked_until=0 WHERE id=1')
        db.update_session(sid, pin_until=time.time()+settings.pin_seconds)


def require_pin(sid):
    session = db.session(sid)
    if session['pin_until'] <= time.time():
        raise PermissionError('Independent PIN verification is required.')
    return session
