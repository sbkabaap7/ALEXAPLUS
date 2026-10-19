# Testing and evidence

Executed on Windows with bundled Python 3.12.14, Node 24.19.0, pnpm 11.25.0, MCP SDK 1.26.0 and downloaded CPU models. Results reflect executed tests, not production assurances.

| Check | Command | Recorded result |
| --- | --- | --- |
| Backend policy/API/persistence/MCP/model suite | `.venv/Scripts/python.exe -m pytest -q` | 119 passed; one upstream Pydantic-settings forward-reference warning |
| Frontend API failure and WAV sample encoding tests | `pnpm --dir frontend test` | 6 passed |
| TypeScript | `pnpm --dir frontend exec tsc -b` | Passed |
| Production bundle | `pnpm --dir frontend build` | Passed |
| Chromium E2E | `pnpm --dir frontend test:e2e` | 4 passed; isolated server, desktop/mobile screenshots |
| Dependency consistency | `.venv/Scripts/python.exe -m pip check` | No broken requirements |

The exact final rerun and additional lifecycle checks, if any, are appended in ME.md.

## What is actually exercised

72 policy combinations; all meaningful voice/occupancy transition combinations; locked/expired/unknown resource denial; SQLite reopening; encrypted template storage; consent and sample counts; PIN hashing/verification/global lockout; origin and tampered-field rejection; enrollment deletion and candidate invalidation; stale inference after deletion; candidate expiry; retention/reset; minimal audit content; disconnected MCP failure.

Actual localhost Streamable HTTP client → initialize asserting **2025-11-25** → discover ten tools → public ALLOW → private DENY → fresh owner voice with no PIN ALLOW → unknown voice restriction → next owner match ALLOW. A voice-request test runs real matching with a fixed private-question transcript, MCP routing, and returns an authorized note without PIN, including after a new browser session. A separate test runs real local Whisper transcription. Create/update reminders and MCP input validation are also called. Injection-like calendar requests cannot change authority.

Real WeSpeaker ONNX executes on separately downloaded public SpeechBrain fixtures. Example1 generates a normalized 256-D embedding. Three explicitly labeled signal-gain variants exercise the enrollment lifecycle; matching the same fixture produces a candidate, and deletion prevents matching. The shorter second fixture is repeated solely to meet the duration minimum and produces cosine similarity approximately 0.177 to the first, classified unknown. This proves model execution on examples; it is not a microphone population benchmark or a liveness test. Local Whisper produces a nonempty English transcript.

Chromium uses explicit fake-device flags backed by that public audio file. The browser still runs real AudioWorklet capture, PCM encoding, live analyser waveform, server VAD/ONNX/STT and MCP. This is an automated test input, not a recording of the owner's microphone. A browser scenario exercises consented three-sample public-fixture enrollment, genuine candidate matching, private access without PIN, template reuse in a new session, private-result clearing on unknown-speaker arrival, access restoration after a new owner match, and PIN-gated template deletion, including a wrong-PIN rejection. Home tests assert denied calendar data before voice verification, one-screen navigation, video looping, and no horizontal page overflow at mobile, tablet, and desktop widths. Screenshots are in `docs/screenshots/` and were visually inspected.

Tests use temporary databases, independent of `data/guestguard.sqlite3`. Browser tests launch their own server with unique temporary persistence. The harness owns exact process IDs to avoid Windows command-shell teardown stalls. Run `scripts.setup_test_fixtures` before model/E2E tests. Model tests skip honestly if weights/fixtures are absent; E2E microphone tests require them. No tests enroll or record the real owner automatically.

## Unverified

Real owner/guest microphone false acceptance and rejection rates; noise and overlap robustness across devices; replay/cloning resistance (not implemented); configured remote LLM provider; Docker build/runtime; Linux execution; external Alexa client/OAuth onboarding; public cloud/TLS deployment. No paid infrastructure, real household account or production biometric guarantee was tested.
