# Developer friction log — actual observations

No Amazon hardware, account onboarding, private APIs or production Alexa connection were exercised. The following entries describe local implementation friction only.

| Task / steps | Expected vs actual | Severity | Workaround | Suggested improvement |
| --- | --- | --- | --- | --- |
| Create venv using Windows Store Python launcher | `py -3.13` existed but executable launch returned access denied | Important | Bundled Python 3.12 created the project venv | Prefer interpreter smoke checks and show executable policy failures separately from missing Python |
| Install Python packages in sandbox | Download expected; WinError 10013 blocked network | Important | Approved dependency-download escalation succeeded | Surface sandbox network denial before pip retries and misleading no-compatible-version messages |
| Reuse MCP server in repeated test lifespans | Expected repeated startup; SDK manager explicitly permits one run only | Important | Fresh FastAPI/MCP application factory per lifecycle | Put the one-shot lifecycle requirement alongside test-client examples |
| Compose MCP with a built SPA | Development wire test passed; built SPA fallback shadowed the bare `/mcp` route | Critical | Compose the SDK's exact ASGI route before SPA fallback and rerun real wire tests with built assets present | Provide tested full-stack route-composition examples, including trailing-slash behavior |
| Run pnpm 11 dependency setup | Packages installed but esbuild postinstall blocked; noninteractive script run tried module reconciliation | Important | Explicitly allowed only esbuild in workspace config; completed offline install | Present build-script approval and noninteractive workspace reconciliation guidance together |
| Real CPU voice model on Windows | Full SpeechBrain stack was heavier than needed | Important | Used officially exported WeSpeaker ONNX + Kaldi-compatible fbank, then executed genuine inference | Publish small end-to-end CPU inference/reference preprocessing tests across OSes |
| Browser mobile navigation | Icon-only mobile controls lost accessible names because labels were display:none | Important | Added explicit aria-label names and reran responsive browser tests | Treat icon-only breakpoint states as required accessibility test cases |
| Validate second public fixture | Expected longer sample; file shorter than 3-second safety minimum | Nice-to-have | Kept fail-closed rejection, no inaccurate different-speaker benchmark claim | Include test fixtures with documented duration, speaker identity relationship and usage terms |

MCP tool discovery, schema validation, structured results and protocol negotiation worked with the pinned SDK after correct lifecycle and route composition. We would use MCP again for this explicit tool boundary. No SDK/Amazon service failure is inferred from untested integrations. Provider-key onboarding and Docker execution remain untested here.
