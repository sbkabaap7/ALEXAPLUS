"""Download public open-source models, never user audio. Run from repo root."""
import os
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
from huggingface_hub import hf_hub_download, snapshot_download
from backend.app.config import settings
from backend.app.voice import MODEL_NAME, MODEL_FILE

settings.model_dir.mkdir(parents=True, exist_ok=True)
hf_hub_download(MODEL_NAME, MODEL_FILE, local_dir=settings.model_dir)
snapshot_download('Systran/faster-whisper-tiny.en', local_dir=settings.model_dir/'whisper')
print('Speaker and English transcription models downloaded. Inference verification is a separate test.')
