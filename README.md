# GuestGuard AI

**Privacy that knows when to speak.** A local voice-aware privacy instrument, built for the Alexa+ MCP track of Build, Ship, Shape 2026. Independent browser simulator; no Echo microphone, Alexa identity, or private Amazon API integration.

GuestGuard combines genuine local WeSpeaker embeddings, a saved owner voice, a management PIN, deterministic policy, and ten real MCP tools. A fresh match to the saved voice opens private requests without a PIN. An unknown voice restricts access until the owner speaks again.

## Run on Windows

Requires Python 3.12, Node 22+, and pnpm 11+. From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
pnpm --dir frontend install --frozen-lockfile
.\.venv\Scripts\python.exe -m scripts.setup_models
pnpm --dir frontend build
.\scripts\start.ps1
```

Open **http://127.0.0.1:8000**. This workspace already has its environment, built UI, and downloaded models. On this machine `scripts/start.ps1` finds the bundled runtime and uses the existing virtual environment. No account or paid service is required. Browser microphone access works on localhost or HTTPS.

1. On Home, open **Voice & PIN** and set a 6–12 digit PIN. This starts a session.
2. In the same dialog, consent and record three short voice samples. Enter the PIN to save the voice. The encrypted template stays saved across sessions until you replace or delete it.
3. Use the Home microphone to make a request. Local English Whisper transcribes it, and GuestGuard checks your voice before invoking protected MCP tools. A match opens calendar, reminders, and notes immediately without another PIN prompt.
4. The voice match stays current for two minutes; record again whenever it expires. The saved voice can be used in a later session without re-enrollment.
5. If an unknown voice is heard, private requests are denied until a fresh owner voice match. No PIN or room-confirmation step is required for ordinary requests. The PIN is used in the Home UI only to save, replace, or delete the stored voice. A session lasts one hour.

Audio is processed in memory and discarded. Templates are Fernet encrypted; PINs are Argon2id hashed. The local key and database are ignored runtime files. Protect the data directory with OS access controls; encryption does not protect against an administrator who can read both files.

## Test

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_test_fixtures
.\.venv\Scripts\python.exe -m pytest -q
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend exec playwright install chromium
pnpm --dir frontend test:e2e
```

Tests use isolated databases and explicitly labeled public SpeechBrain audio fixtures, never your microphone or owner vault. See [testing](docs/testing.md) for actual results and scope. For frontend development, run the backend and `pnpm --dir frontend dev`; Vite proxies API calls to port 8000.

## Architecture

React/TypeScript/Vite → FastAPI → SQLite + deterministic policy. AudioWorklet → mono PCM WAV → validation/resampling/WebRTC VAD → Kaldi-compatible fbank → WeSpeaker ResNet34 ONNX cosine matching. Local faster-whisper transcribes English. The backend agent initializes a real MCP HTTP client, discovers tools and invokes them through the authenticated `/mcp` endpoint. Private rows are fetched only after policy allows access.

Ten tools: `get_privacy_state`, `get_public_home_status`, `list_calendar_events`, `list_reminders`, `read_personal_note`, `get_home_device_status`, `create_reminder`, `update_reminder`, `get_access_decision`, `get_privacy_activity_summary`.

The backend still supports external MCP clients through the PIN-protected `POST /api/mcp/credential` endpoint. The simplified Home UI does not expose credential management. Configure Streamable HTTP at `http://127.0.0.1:8000/mcp` with `Authorization: Bearer <credential>`. Credentials expire/revoke with their application session. Tested wire negotiation: **2025-11-25**, SDK **1.26.0**. This custom local bearer scheme is not an Alexa OAuth onboarding implementation.

## Local answers and protected actions

GuestGuard uses local Ollama with `qwen3:4b-instruct` for general questions. The standalone copy at `tools/ollama/ollama.exe`, when present, is started by `scripts/start.ps1`; its models live in `models/ollama`. On another machine, install Ollama for Windows and run `ollama pull qwen3:4b-instruct`. Override `GUESTGUARD_OLLAMA_BASE_URL` (local HTTP only) or `GUESTGUARD_OLLAMA_MODEL` in `.env` if needed. Health shows whether the configured model is installed. If it is unavailable, general questions receive a clear setup message, while supported GuestGuard actions still work.

Calendar, notes, confidential/account records, reminders, home, and privacy requests continue through the MCP client and server-owned policy. “Read it again” repeats the previous read tool for up to five minutes and rechecks policy. No MCP result, private record, or tool transcript is sent to Ollama; only the current general question is sent to the local model. The older OpenAI-compatible tool-selection configuration remains optional in `.env` for deployments that deliberately use it; configuring it sends the request text to that provider. Voice embeddings and raw audio stay local.

## Limitations and submission status

Prototype thresholds are not calibrated to your microphone or population. Voice alone now opens private data, so replay, cloning, or a false match can expose it; no liveness or reliable overlapping-speaker detection. Segment consistency is only a conservative heuristic. Initial PIN setup assumes a trusted local machine. State is session-scoped, not a room-wide multi-device monitor. Protected actions use keyword routing unless an optional tool-selection provider is configured; general answers require local Ollama. Synthetic records/device configuration are labeled. No live weather or real household connectors. Do not use as production biometric authentication.

Cloud deployment and GitHub/Devpost publication have not been performed. Docker configuration and submission materials are provided; a demo video, repository URL, registration/eligibility review, and any deployment require owner action/authorization. Read [architecture](docs/architecture.md), [security model](docs/security-model.md), [demo script](docs/demo-script.md), [submission checklist](docs/submission-checklist.md), and [engineering memory](ME.md).
