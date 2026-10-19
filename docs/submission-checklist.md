# Submission checklist

Official rules checked 2026-10-16: [Build, Ship, Shape rules](https://amazonappdev2026.devpost.com/rules). Deadline: **2026-10-23 12:00 PDT = 2026-10-24 00:30 IST**. The Alexa+ route accepts a self-hosted server implementing MCP 2025-11-25 over Streamable HTTP, with an optional independent web simulator. A GitHub repository, English description, under-three-minute public YouTube/Vimeo demo, track choice and product feedback are required. The owner must recheck eligibility and terms before submitting; nothing has been submitted.

- [x] Real MCP server/client imported and called at runtime; 2025-11-25 asserted by integration test.
- [x] Deterministic backend policy; voice-gated private fetch; PIN-gated template enrollment and deletion.
- [x] Real ONNX embedding and local Whisper executed on public fixtures.
- [x] Consent/enrollment/deletion controls, synthetic seed data and truthful limitations.
- [x] One-screen React Home with Voice & PIN setup and local instructions.
- [x] MIT license for project code; third-party notices and upstream links.
- [x] Devpost description, demo script, architecture, security model, engineering memory and friction log.
- [ ] Owner enrolls their own voice with consent and rehearses a two-speaker demonstration.
- [ ] Confirm voice threshold behavior on the actual microphone; do not claim an accuracy benchmark.
- [ ] Record and publicly upload a truthful video under three minutes (YouTube/Vimeo).
- [ ] Publish a GitHub repository, or share a private repository with the required judges listed in the current official rules.
- [ ] Review repository contents to exclude `.env`, data/models/audio, PINs, session/MCP tokens and biometric templates.
- [ ] Supply repository/video URLs, owner/team identity, eligibility and registration information.
- [ ] Owner authorizes publishing/submitting and submits before the deadline.
- [ ] If choosing Docker or cloud hosting, execute and verify the prepared configuration first; no deployment was performed.

This project has no AWS runtime integration and makes no AWS Builder mini-challenge claim. Open Source mini-challenge rules require an additional qualifying contribution and its URLs; the included project license alone is not represented as satisfying that separate requirement.
