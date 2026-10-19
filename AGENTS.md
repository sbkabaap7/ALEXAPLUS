# GuestGuard AI engineering instructions

Read this file and ME.md at the start of each session. Continue the last incomplete milestone; preserve working code.

Build a local React/TypeScript + Python/SQLite prototype with genuine MCP Streamable HTTP and speaker embeddings. Never claim Alexa integration, liveness, production biometric security, or unexecuted tests. Simulated events and deterministic agent fallback must be visibly labeled.

Authorization is deterministic and server owned. The saved owner voice persists across sessions; a fresh match grants personal and sensitive access without a PIN. Unknown/uncertain audio restricts access until the next owner match, which clears Guest Mode. In the Home user flow, PIN is requested only for saving, replacing, or deleting the enrolled voice. No frontend role fields may grant authority. Filter data before any LLM sees it.

Use parameterized SQL, expiring sessions, hashed PINs, protected templates, authenticated MCP, input limits, and privacy-minimal audit logs. Never commit runtime data, recordings, keys, templates, PINs or transcripts. Do not record without user action and consent. Do not publish or deploy without owner authorization.

Append a concise chronological ME.md entry after each meaningful milestone and at session end. Each entry must contain Objective, Changes Made, Files Affected, Reasoning, Alternatives, Verification, Results, Problems Encountered, Next Steps. Record actual commands/results and pending work honestly. Never include private/biometric/credential values. Runtime audit events are separate from ME.md.

Run meaningful policy, API, actual MCP integration, voice, frontend and supported E2E tests. Fix failures; preserve accurate limitations. Use Windows-compatible startup scripts. All visible controls must work.
