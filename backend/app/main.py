import asyncio
import hashlib
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Response, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .config import settings
from .security import db, passwords, create_session, current_session, verify_pin, require_pin, mcp_token
from .privacy import evaluate, voice_transition
from .tools import public_state
from .mcp_server import create_mcp
from .agent import run_agent
from .ollama import model_ready
from . import voice
from .transcription import transcribe
from .streaming import stream_agent


def create_app():
    mcp = create_mcp()
    preview_lock = asyncio.Semaphore(1)
    @asynccontextmanager
    async def lifespan(app):
        async with mcp.session_manager.run():
            yield
    
    
    app = FastAPI(title='GuestGuard AI', version='0.1.0', lifespan=lifespan, docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
    
    
    @app.middleware('http')
    async def boundaries(request: Request, call_next):
        origin = request.headers.get('origin')
        # Exact same-origin checking blocks browser cross-site requests and DNS-rebinding attacks.
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': 'Cross-origin request rejected'}, status_code=403)
        marker = None
        if request.url.path.startswith('/mcp'):
            authorization = request.headers.get('authorization', '')
            if not authorization.startswith('Bearer '):
                return JSONResponse({'detail': 'MCP bearer credential required'}, status_code=401)
            digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
            row = db.one('SELECT id FROM sessions WHERE mcp_hash=?', (digest,))
            try:
                if not row:
                    raise PermissionError()
                db.session(row['id'])
                marker = current_session.set(row['id'])
            except PermissionError:
                return JSONResponse({'detail': 'MCP credential expired or invalid'}, status_code=401)
        try:
            response = await call_next(request)
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Referrer-Policy'] = 'no-referrer'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'"
            response.headers['Permissions-Policy'] = 'microphone=(self), camera=()'
            return response
        finally:
            if marker:
                current_session.reset(marker)
    
    
    @app.exception_handler(PermissionError)
    async def permission_error(request, exc):
        return JSONResponse({'detail': str(exc) or 'Access denied'}, status_code=403)
    
    
    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=400)
    
    
    def sid(request):
        token = request.cookies.get('gg_session', '')
        db.session(token)
        return token
    
    
    class StrictModel(BaseModel):
        model_config = ConfigDict(extra='forbid')
    
    
    class PinBody(StrictModel):
        pin: str = Field(pattern=r'^\d{6,12}$')
    
    
    class ConfirmBody(StrictModel):
        confirmed: bool
    
    
    class MessageBody(StrictModel):
        text: str = Field(min_length=1, max_length=2000)
    
    
    class OccupancyBody(StrictModel):
        state: str = Field(pattern=r'^(GUEST_DETECTED|UNCERTAIN)$')
    
    
    class RulesBody(StrictModel):
        audit_days: int = Field(ge=1, le=30)
    
    
    @app.get('/api/health')
    def health():
        return {'status': 'online', 'mcp_sdk': '1.26.0', 'transport': 'Streamable HTTP', 'voice': voice.model_status(),
                'stt_available': (settings.model_dir/'whisper'/'model.bin').exists(),
                'agent': f'Local Ollama · {settings.ollama_model}' if model_ready() else 'Local Ollama unavailable (tool replies still work)',
                'pin_configured': db.one('SELECT id FROM users WHERE id=1') is not None}
    
    
    @app.post('/api/session')
    def start_session(request: Request, response: Response):
        # A fresh session invalidates the prior browser credential and its MCP derivative.
        previous = request.cookies.get('gg_session', '')
        if previous:
            db.execute('DELETE FROM sessions WHERE id=?', (previous,))
        token = create_session()
        response.set_cookie('gg_session', token, httponly=True, samesite='strict', secure=settings.cookie_secure, max_age=settings.session_seconds, path='/')
        return public_state(db.session(token))
    
    
    @app.get('/api/state')
    def state(request: Request):
        token = sid(request)
        return public_state(db.session(token))
    
    
    @app.post('/api/pin/setup')
    def pin_setup(body: PinBody, request: Request):
        token = sid(request)
        with db.lock:
            if db.one('SELECT id FROM users WHERE id=1'):
                raise PermissionError('Owner PIN already configured.')
            db.execute('INSERT INTO users(id,pin_hash) VALUES (1,?)', (passwords.hash(body.pin),))
        verify_pin(token, body.pin)
        return {'configured': True}
    
    
    @app.post('/api/pin/verify')
    def pin_verify(body: PinBody, request: Request):
        token = sid(request)
        verify_pin(token, body.pin)
        db.audit(db.session(token), 'verify_pin', 'PUBLIC', 'ALLOW', 'INDEPENDENT_FACTOR_VERIFIED')
        return public_state(db.session(token))
    
    
    @app.post('/api/guest/clear')
    def clear_guest(body: ConfirmBody, request: Request):
        token = sid(request)
        with db.lock:
            session = require_pin(token)
            if not body.confirmed:
                raise ValueError('Confirm the guest has left before clearing presence.')
            db.update_session(token, guest_presence='CLEAR')
            db.audit(session, 'clear_guest_presence', 'PUBLIC', 'ALLOW', 'PIN_AND_EXPLICIT_ROOM_CONFIRMATION')
            return public_state(db.session(token))
    
    
    @app.post('/api/guest/simulate')
    def simulate(body: OccupancyBody, request: Request):
        token = sid(request)
        with db.lock:
            session = db.session(token)
            db.update_session(token, guest_presence=body.state, speaker_status='UNKNOWN_SPEAKER' if body.state == 'GUEST_DETECTED' else 'UNCERTAIN', pin_until=0, similarity=None)
            db.audit(session, 'simulate_occupancy', 'PUBLIC', 'ALLOW', 'LABELED_SIMULATION_'+body.state)
            return public_state(db.session(token))
    
    
    @app.post('/api/session/lock')
    def lock_session(request: Request):
        token = sid(request)
        db.update_session(token, locked=1, pin_until=0)
        return {'locked': True}
    
    
    @app.get('/api/identity')
    def identity(request: Request):
        sid(request)
        row = db.one('SELECT sample_count,consent_at,model FROM voice_enrollments WHERE id=1')
        return {'enrolled': bool(row), 'enrollment': row, 'model': voice.model_status()}
    
    
    async def bounded_read(file):
        raw = await file.read(4_000_001)
        await file.close()
        if len(raw) > 4_000_000:
            raise ValueError('Audio exceeds 4 MB.')
        return raw
    
    
    @app.post('/api/identity/enroll')
    async def enroll(request: Request, consent: bool = Form(...), samples: list[UploadFile] = File(...)):
        token = sid(request)
        require_pin(token)
        if not consent or len(samples) != 3:
            raise ValueError('Explicit consent and exactly three voice samples are required.')
        raw = [await bounded_read(file) for file in samples]
        # Inference runs off the event loop; auth is rechecked at the storage boundary.
        def work():
            with db.lock:
                require_pin(token)
                result = voice.enroll(raw, authorize=lambda: require_pin(token))
                db.audit(db.session(token), 'enroll_voice', 'SENSITIVE', 'ALLOW', 'PIN_AND_BIOMETRIC_CONSENT')
                return result
        return await asyncio.to_thread(work)
    
    
    @app.delete('/api/identity')
    def delete_identity(request: Request):
        token = sid(request)
        with db.lock:
            session = require_pin(token)
            db.execute('DELETE FROM voice_enrollments')
            db.execute("UPDATE sessions SET speaker_status='UNCERTAIN',pin_until=0,similarity=NULL,last_voice_at=0")
            db.audit(session, 'delete_enrollment', 'SENSITIVE', 'ALLOW', 'OWNER_REQUESTED_DELETION')
        return {'deleted': True}
    
    
    @app.post('/api/voice/start')
    def begin_voice(request: Request):
        token = sid(request)
        with db.lock:
            current = db.session(token)
            changes = voice_transition(current, 'UNCERTAIN')
            changes['last_voice_at'] = time.time()
            db.update_session(token, **changes)
        return public_state(db.session(token))


    @app.post('/api/voice/preview')
    async def preview_voice(request: Request, audio: UploadFile = File(...)):
        token = sid(request)
        # Preview text never runs tools or establishes a speaker identity.
        with db.lock:
            current = db.session(token)
            changes = voice_transition(current, 'UNCERTAIN')
            changes['last_voice_at'] = time.time()
            db.update_session(token, **changes)
        raw = await bounded_read(audio)
        if preview_lock.locked():
            raise HTTPException(status_code=429, detail='Transcription is busy. Continue speaking.')
        async with preview_lock:
            def work():
                speech, _, _ = voice.preprocess(raw)
                return transcribe(speech)
            try:
                transcript = await asyncio.wait_for(asyncio.to_thread(work), timeout=30)
            except voice.AudioError:
                return {'text': '', 'available': True, 'message': 'Keep speaking…'}
            except asyncio.TimeoutError:
                return {'text': '', 'available': False, 'message': 'Live transcription is taking too long. Your recording will be checked when you stop.'}
        sid(request)
        return transcript


    @app.post('/api/voice')
    async def voice_request(request: Request, audio: UploadFile = File(...)):
        token = sid(request)
        # Revoke privileges before reading or decoding any submitted sample.
        started = time.time()
        with db.lock:
            session = db.session(token)
            db.update_session(token, speaker_status='UNCERTAIN', similarity=None, pin_until=0, last_voice_at=started)
            enrolled_before = db.one('SELECT consent_at FROM voice_enrollments WHERE id=1')
        try:
            raw = await bounded_read(audio)
            speech, assessment = await asyncio.wait_for(asyncio.to_thread(voice.verify, raw), timeout=45)
        except (voice.AudioError, asyncio.TimeoutError, ValueError) as exc:
            with db.lock:
                current = db.session(token)
                if current['last_voice_at'] == started:
                    db.update_session(token, **voice_transition(current, 'INVALID_AUDIO'))
                    db.audit(current, 'verify_voice', 'PUBLIC', 'DENY', 'INVALID_OR_UNAVAILABLE_AUDIO')
            raise ValueError(str(exc) or 'Voice processing timed out. Identity remains restricted.')
        with db.lock:
            current = db.session(token)
            enrolled_now = db.one('SELECT consent_at FROM voice_enrollments WHERE id=1')
            if current['last_voice_at'] != started or enrolled_before != enrolled_now:
                raise ValueError('Voice assessment superseded by newer input or enrollment changes. Record again.')
            changes = voice_transition(current, assessment['speaker_status'])
            changes.update(similarity=assessment['similarity'], last_voice_at=time.time())
            db.update_session(token, **changes)
            db.audit(db.session(token), 'verify_voice', 'PUBLIC', 'ALLOW', assessment['speaker_status'])
        try:
            transcript = await asyncio.wait_for(asyncio.to_thread(transcribe, speech), timeout=45)
        except Exception:
            transcript = {'text': '', 'available': False, 'message': 'Transcription failed. No transcript was fabricated.'}
        agent = await run_agent(token, transcript['text']) if transcript['text'] else None
        return {'assessment': assessment, 'transcript': transcript, 'agent': agent, 'state': public_state(db.session(token))}
    
    
    @app.post('/api/agent')
    async def agent(body: MessageBody, request: Request):
        return await run_agent(sid(request), body.text)


    @app.post('/api/agent/stream')
    async def agent_stream(body: MessageBody, request: Request):
        token = sid(request)
        return StreamingResponse(stream_agent(token, body.text), media_type='application/x-ndjson',
                                 headers={'X-Accel-Buffering': 'no'})
    
    
    @app.get('/api/history')
    def history(request: Request, decision: str = '', tool: str = ''):
        token = sid(request)
        rules = db.one('SELECT * FROM privacy_rules WHERE id=1')
        db.execute('DELETE FROM privacy_audit_events WHERE timestamp<?', (time.time()-rules['audit_days']*86400,))
        return db.all('SELECT * FROM privacy_audit_events WHERE session_id=? AND (?=\'\' OR decision=?) AND (?=\'\' OR tool LIKE ?) ORDER BY id DESC LIMIT 200', (token[:8], decision, decision, tool, '%'+tool+'%'))
    
    
    @app.delete('/api/history')
    def delete_history(request: Request):
        token = sid(request)
        require_pin(token)
        db.execute('DELETE FROM privacy_audit_events WHERE session_id=?', (token[:8],))
        return {'deleted': True}
    
    
    @app.get('/api/rules')
    def rules(request: Request):
        sid(request)
        scenarios = {
            'Verified owner': {'speaker_status': 'OWNER_CANDIDATE', 'guest_presence': 'CLEAR', 'pin_until': time.time()+300},
            'Owner candidate': {'speaker_status': 'OWNER_CANDIDATE', 'guest_presence': 'CLEAR', 'pin_until': 0},
            'Unknown speaker': {'speaker_status': 'UNKNOWN_SPEAKER', 'guest_presence': 'CLEAR', 'pin_until': 0},
            'Guest present': {'speaker_status': 'OWNER_CANDIDATE', 'guest_presence': 'GUEST_DETECTED', 'pin_until': time.time()+300},
            'Uncertain identity': {'speaker_status': 'UNCERTAIN', 'guest_presence': 'UNCERTAIN', 'pin_until': 0}}
        rows = []
        for label, sensitivity in [('Public information', 'PUBLIC'), ('Personal reminders', 'PERSONAL'), ('Calendar events', 'PERSONAL'), ('Private notes', 'PERSONAL'), ('Sensitive account data', 'SENSITIVE')]:
            cells = {}
            for name, scenario in scenarios.items():
                result = evaluate(scenario | {'expires_at': time.time()+300}, sensitivity)
                cells[name] = {'decision': str(result.decision), 'reason': result.reason}
            rows.append({'label': label, 'sensitivity': sensitivity, 'cells': cells})
        return {'matrix': rows, 'settings': db.one('SELECT audit_days FROM privacy_rules WHERE id=1')}
    
    
    @app.put('/api/rules')
    def save_rules(body: RulesBody, request: Request):
        require_pin(sid(request))
        db.execute('UPDATE privacy_rules SET audit_days=? WHERE id=1', (body.audit_days,))
        return {'saved': True}
    
    
    @app.post('/api/mcp/credential')
    def credential(request: Request):
        token = sid(request)
        require_pin(token)
        return {'token': mcp_token(token), 'endpoint': settings.base_url+'/mcp', 'expires_at': db.session(token)['expires_at']}
    
    
    @app.post('/api/data/reset')
    def reset(body: ConfirmBody, request: Request, response: Response):
        token = sid(request)
        with db.lock:
            require_pin(token)
            if not body.confirmed:
                raise ValueError('Explicit reset confirmation required')
            with db.connect() as connection:
                for table in ('voice_enrollments', 'sessions', 'privacy_audit_events', 'users', 'reminders'):
                    connection.execute(f'DELETE FROM {table}')
                connection.execute("INSERT INTO reminders(title) VALUES ('Synthetic: collect library books')")
                connection.execute('UPDATE privacy_rules SET audit_days=7 WHERE id=1')
        response.delete_cookie('gg_session', path='/')
        return {'reset': True}
    
    
    # Mount last so explicit API routes and the local production UI remain reachable.
    app.router.routes.extend(mcp.streamable_http_app().routes)
    frontend = Path('frontend/dist')
    if frontend.exists():
        app.mount('/assets', StaticFiles(directory=frontend/'assets'), name='assets')
        @app.get('/{path:path}')
        def spa(path: str):
            if path.startswith('api/'):
                raise HTTPException(404, 'Unknown endpoint')
            return FileResponse(frontend/'index.html')
    return app


app = create_app()
