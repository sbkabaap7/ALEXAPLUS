# Security model

Prototype for a single trusted local owner. Browser simulator, not Alexa+ integration. No passive monitoring, liveness or spoof-proof authentication.

## Trust boundaries
Microphone audio and transcripts are untrusted. Speaker similarity is probabilistic. Frontend role and occupancy claims cannot grant privileges. Server session state and deterministic policy decide access before fetching private data or sending results to a model. MCP validates bearer credentials bound to an application session.

The general-question model endpoint is restricted to loopback HTTP. Only the current general question is passed to local Ollama; MCP results and private records are never added to its prompt. Protected requests stay on the server-owned policy path even when a model is available.

## Invariants
Public tools may return explicitly public synthetic household data. Personal/sensitive tools need a current owner voice match. Unknown/uncertain/invalid audio restricts access, and the next valid owner match restores it, even after Guest Mode was detected. The Home UI requests a PIN only for saving, replacing, or deleting the voice template. Expired/locked sessions deny all operations.

## Risks and mitigations
Replay/voice cloning and false matches can authorize private data because voice is the access factor. There is no liveness check; an owner-like voice can also clear Guest Mode even if someone else remains present. This mode is unsuitable for high-stakes or production privacy. PIN guessing is limited with a password hash, attempt limits, and temporary lockout; PIN protects enrollment and deletion in the Home UI. Stolen session: high-entropy HttpOnly cookie, expiry, same-origin mutation checks; use TLS for deployment. MCP calls require separate session-bound bearer credentials; never publish them. Prompt injection: tools enforce the same policy regardless of model output. Biometric leakage: encrypted templates, no raw audio retention, deletion, ignored data directory.

Multiple overlapping speakers cannot reliably be separated by this MVP; document model/segment consistency limits. Do not use it as a production security boundary. Shared local machine administrator compromise, shoulder-surfed PINs, malicious extensions and OS compromise remain outside the prototype's protection.

## Implemented boundaries and practical limits
MCP 1.26.0 exposes exact SDK routes at /mcp; actual client initialization asserts 2025-11-25. Local session-specific bearer authentication is custom and does not implement production OAuth discovery. A trusted local owner sets the first PIN; do not expose bootstrap on a public server. Hostnames are restricted to localhost/127.0.0.1. Requests with a cross-origin Origin are rejected. High-entropy browser cookies are HttpOnly and SameSite=Strict; secure-cookie mode is configurable for TLS. PIN attempts are serialized and limited across all sessions. Settings edits cannot weaken access invariants.

Candidate evidence expires after 120 seconds, PIN management verification after 300 seconds, session after 3600 seconds by default. Starting a fresh browser session invalidates its old credential. Model input is bounded to 4 MB WAV/20 seconds, with minimum 3 seconds and at least 2 seconds VAD speech. New audio revokes prior candidate evidence before decoding. Stale inference cannot restore deleted/rotated enrollment or supersede newer input. Templates are Fernet encrypted with an ignored local key; on Windows, apply proper user ACLs because chmod is not a substitute for an ACL. SQLite deletion is logical deletion; storage forensics, backups and securely wiping physical media are not guaranteed. Raw recordings are not persisted by the app.

The browser refreshes server state every four seconds and clears displayed private tool results on authorization downgrade. Already viewed information cannot be recalled; the prototype does not guarantee instant cross-tab screen blanking. State is per application session; an event in one independent session is not a global multi-device occupancy event. Local denial-of-service, exhaustive upload abuse and compromised local administrators are outside this MVP's production protections. No reliable anti-spoofing or overlapping-speaker detector is implemented.
