# Third-party components and model provenance

Project code is MIT licensed. Dependencies retain their respective licenses; installing or using models does not relicense them under this project's MIT license.

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk): MIT.
- [WeSpeaker](https://github.com/wenet-e2e/wespeaker): Apache-2.0 toolkit; [official ResNet34 model repository](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34). Model downloaded at setup, not bundled in source. Review the upstream model/dataset terms for redistribution and your intended use.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper): MIT; [tiny.en converted model](https://huggingface.co/Systran/faster-whisper-tiny.en).
- [SpeechBrain example fixture source](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/tree/main): public example1.wav/example2.flac downloaded separately for automated execution tests; not redistributed as part of the code repository, never represented as consenting owner enrollment.
- IBM Plex Sans/Mono: SIL Open Font License via [IBM Plex](https://github.com/IBM/plex) and Fontsource packages. Fonts are served locally; npm package license files retain the applicable notices.
- React, Vite, Lucide, FastAPI, SQLite, NumPy, SciPy, cryptography, Argon2, ONNX Runtime, WebRTC VAD and Kaldi-native-fbank retain upstream licenses. Dependency lockfiles specify installed versions.

No copied Alexa/Amazon logos, third-party music or other branding is included. Screenshots show synthetic application data. Before distributing a compiled binary/container with dependencies or models, include all applicable upstream license files/notices and confirm model/data usage terms.
