# Demo script — target 2 minutes 50 seconds

Prepare a quiet room, two consenting speakers and three fresh enrollment samples. Run the local app and confirm model status. Use only synthetic private records. Do not show PINs, bearer credentials or template files. Record actual interactions; label edits/time compression and every simulated event. The official video requirement is under three minutes.

| Time | Screen / action | Narration |
| --- | --- | --- |
| 0:00–0:15 | Home, restricted initial state | “Assistants know private things. The room does not always stay private. GuestGuard makes privacy a server-enforced decision.” |
| 0:15–0:40 | Voice & PIN dialog: consent, three genuine samples, PIN-authenticated save; trim waiting transparently | “A local pretrained model stores an encrypted embedding. Recordings are discarded.” |
| 0:40–1:00 | Home mic: owner records calendar request; show immediate permitted response without PIN through real MCP | “A fresh match to the saved voice opens the synthetic calendar. This convenience also makes spoofed voices a real risk.” |
| 1:00–1:25 | Second speaker records “Read my private calendar” | “An unknown speaker restricts private access. The MCP tool denies the request before private records are fetched.” |
| 1:25–1:45 | Owner records the same request again | “A fresh match to the saved owner voice restores access without a PIN.” |
| 1:45–2:05 | Start a new session; owner asks again in their saved voice | “The voice template stays saved across sessions. Each new match can open private requests.” |
| 2:05–2:25 | Home: ask for the protected note; show the blocked or allowed response | “Sensitive access follows the same deterministic policy. The agent discovers and calls real tools over Streamable HTTP 2025-11-25.” |
| 2:25–2:40 | Home: try an impersonation request; show deletion in Voice & PIN if time permits | “Claiming to be the owner changes nothing. Decisions are recorded without transcripts or private contents.” |
| 2:40–2:50 | Home | “Privacy that knows when to speak. A local MCP prototype—not a production biometric system or an official Alexa integration.” |

If no second consenting speaker is available, a developer may use the backend guest simulation endpoint and clearly label that occupancy event as simulated. Do not describe it as a real unknown-voice test. Keep genuine owner recording/model output in the demo. No demo video has been recorded or published by this implementation session.
