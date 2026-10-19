# Implementation roadmap

0. Workspace, persistent memory, threat boundaries.
1. SQLite schema, typed policy, sessions, PIN and tests.
2. Authenticated MCP Streamable HTTP server and real client integration tests (2025-11-25).
3. Genuine pretrained voice embeddings, quality validation, encrypted enrollment templates.
4. Voice-gated access, guest restriction until the next owner match, expiry and deletion.
5. Local speech-to-text and optional configurable LLM; labeled deterministic fallback.
6. Single-screen React Home with Voice & PIN enrollment and management.
7. Backend/frontend/E2E tests; fix observed failures and review privacy boundaries.
8. Docker/Windows startup, README, architecture, testing, demo and truthful submission materials.

Status: Phase 0 complete. All later work pending at initial creation. ME.md is the chronological source of execution results.

## Implemented status (2026-10-16)
Phases 0–7 implemented and tested as a local MVP, including genuine CPU voice and local STT, real MCP, server-owned voice-only access, a single Home view, and four Chromium scenarios. Phase 8 documentation and deployment recipes prepared; actual Docker/cloud execution, owner enrollment/rehearsal, recording/publication and Devpost submission remain pending. No claim of production accuracy or official Alexa integration. See ME.md and docs/testing.md for exact results.
