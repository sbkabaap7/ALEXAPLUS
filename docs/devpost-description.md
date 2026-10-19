# GuestGuard AI — Privacy that knows when to speak

## Inspiration
GuestGuard lets an enrolled owner ask for private information by voice without entering a PIN for each request. An unknown voice temporarily restricts access until the owner speaks again.

## What it does
GuestGuard is a browser-based privacy assistant with genuine local speaker embeddings and a self-hosted MCP server. A fresh match to the saved owner voice opens private calendar events, notes, and reminders without a PIN prompt. The voice template persists across sessions until the owner replaces or deletes it using a PIN. An unknown speaker restricts private access; the next valid owner match restores it.

The single-screen console lets people ask by voice or text and manage voice enrollment through Voice & PIN. Enrollment is consent-based; encrypted templates can be deleted. Actual microphone capture and local English transcription feed the enforced MCP access decision.

## How we built it
React, TypeScript and Vite provide the Home interface. FastAPI and SQLite own application state. A WeSpeaker ResNet34 ONNX model generates real 256-dimensional speaker embeddings from Kaldi-compatible filterbank features after WebRTC VAD. Local faster-whisper provides speech-to-text. The MCP Python SDK 1.26.0 serves ten tools over Streamable HTTP; integration tests assert actual 2025-11-25 negotiation and allowed/denied protected tool calls. A shared deterministic policy gates private database fetches before any result can reach an agent. Local Ollama answers general questions, while protected requests run through the MCP policy.

## What is different
The central feature is a voice-gated MCP boundary. A fresh owner match opens private data without repeated PIN entry, while an unknown voice blocks it until the owner is heard again. A conversational claim cannot change authority, and an LLM cannot bypass server policy. The demo shows blocked data at the MCP boundary rather than merely changing a badge.

## Challenges and learning
We verified protocol compatibility on the wire, corrected lifecycle and SPA routing issues, selected an ONNX model for Windows CPU compatibility, and kept all simulated occupancy events visibly labeled. We learned that conservative state transitions and truthful failure states matter as much as the recognition score. See the engineering journal and friction log for actual commands and results.

## Limitations
This is an independent browser simulator for the Alexa+ MCP track, not an official Alexa integration. No Echo microphones, Alexa identities or private APIs are connected. Voice replay, cloning, and false matches can expose private data because voice is the access factor; no liveness is implemented. An owner match can restore access while another person is still present. Thresholds need calibration, overlapping speakers are not reliably detected, and initial owner setup assumes a trusted local machine. Household records and devices are synthetic. Docker and public deployment have not been verified. Do not describe this prototype as production biometric security.

## Next steps
Record a truthful consented two-speaker demonstration, benchmark false accept/reject behavior across microphones, evaluate anti-spoofing, and design production OAuth/session and secure bootstrap boundaries before actual multi-device integration.

Primary track: Alexa+ / self-hosted MCP server with independent browser simulator. No AWS Builder mini-challenge claim: no AWS runtime service was integrated. Repository URL and demo video URL must be supplied by the owner before submission.
