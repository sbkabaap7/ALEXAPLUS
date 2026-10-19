"""Optional local faster-whisper. Missing models never fabricate a transcript."""
import threading
from .config import settings

_model = None
_lock = threading.Lock()


def transcribe(audio):
    global _model
    path = settings.model_dir / 'whisper'
    if not (path / 'model.bin').exists():
        return {'text': '', 'available': False, 'message': 'Local speech-to-text model unavailable. Use the labeled typed request field.'}
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel
            _model = WhisperModel(str(path), device='cpu', compute_type='int8', cpu_threads=2)
        segments, _ = _model.transcribe(audio, beam_size=1, vad_filter=False, language='en')
        text = ' '.join(part.text.strip() for part in segments).strip()
    return {'text': text, 'available': True, 'message': 'Local faster-whisper / tiny.en'}
