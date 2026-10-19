"""Real WeSpeaker ResNet34 ONNX inference. No synthetic identity promotion."""
import io
import json
import math
import threading
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from .config import settings
from .security import db, cipher

MODEL_NAME = 'Wespeaker/wespeaker-voxceleb-resnet34'
MODEL_FILE = 'voxceleb_resnet34.onnx'
_model = None
_lock = threading.Lock()


class AudioError(ValueError):
    pass


def preprocess(raw: bytes):
    if not 44 <= len(raw) <= 4_000_000:
        raise AudioError('Audio must be a WAV file under 4 MB.')
    try:
        with sf.SoundFile(io.BytesIO(raw)) as file:
            if file.format != 'WAV' or file.frames / file.samplerate > 20 or file.channels > 2:
                raise AudioError('Use mono/stereo WAV, no longer than 20 seconds.')
            audio = file.read(dtype='float32', always_2d=True).mean(axis=1)
            rate = file.samplerate
    except AudioError:
        raise
    except Exception as exc:
        raise AudioError('Invalid or unsupported WAV audio.') from exc
    if not 8000 <= rate <= 96000 or not np.isfinite(audio).all():
        raise AudioError('Invalid sample rate or samples.')
    if len(audio) / rate < 3:
        raise AudioError('Record at least 3 seconds of clear speech.')
    if np.mean(np.abs(audio) > 0.98) > 0.02:
        raise AudioError('Audio is clipped. Move away from the microphone.')
    divisor = math.gcd(rate, 16000)
    audio = resample_poly(audio, 16000//divisor, rate//divisor).astype(np.float32)
    rms = float(np.sqrt(np.mean(audio**2)))
    if rms < 0.003:
        raise AudioError('Audio is too quiet. Speak closer to the microphone.')
    import webrtcvad
    vad = webrtcvad.Vad(2)
    pcm = (np.clip(audio, -1, 1)*32767).astype('<i2')
    voiced = []
    for offset in range(0, len(pcm)-480+1, 480):
        if vad.is_speech(pcm[offset:offset+480].tobytes(), 16000):
            voiced.append(audio[offset:offset+480])
    duration = len(voiced)*0.03
    if duration < 2:
        raise AudioError('Not enough detected speech. Record 5–10 seconds in a quiet room.')
    return audio, np.concatenate(voiced), {'duration': round(len(audio)/16000, 2), 'speech_seconds': round(duration, 2), 'rms': round(rms, 4), 'vad': 'WebRTC VAD, mode 2'}


def model_status():
    return {'name': MODEL_NAME, 'available': (settings.model_dir/MODEL_FILE).exists(), 'loaded': _model is not None,
            'threshold': settings.voice_threshold, 'margin': settings.voice_margin, 'liveness': False}


def model():
    global _model
    with _lock:
        if _model is None:
            import onnxruntime as ort
            path = settings.model_dir/MODEL_FILE
            if not path.exists():
                raise AudioError('Speaker model unavailable. Run the model setup script; identity remains restricted.')
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            _model = ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])
    return _model


def embed(audio: np.ndarray):
    import kaldi_native_fbank as knf
    options = knf.FbankOptions()
    options.frame_opts.samp_freq = 16000
    options.frame_opts.dither = 0
    options.frame_opts.window_type = 'hamming'
    options.mel_opts.num_bins = 80
    options.mel_opts.low_freq = 20
    bank = knf.OnlineFbank(options)
    bank.accept_waveform(16000, (audio*32768).tolist())
    bank.input_finished()
    features = np.stack([bank.get_frame(i) for i in range(bank.num_frames_ready)]).astype(np.float32)
    features -= features.mean(axis=0, keepdims=True)
    session = model()
    vector = session.run(None, {session.get_inputs()[0].name: features[None, :, :]})[0].reshape(-1)
    norm = np.linalg.norm(vector)
    if not np.isfinite(vector).all() or norm < 1e-8:
        raise AudioError('Speaker model returned an unusable embedding.')
    return vector/norm


def extract(raw):
    audio, voiced, quality = preprocess(raw)
    vector = embed(voiced)
    # A consistency heuristic can reject sequential speaker changes, but is not diarization/liveness.
    if len(voiced) >= 16000*6:
        parts = np.array_split(voiced, 2)
        consistency = float(embed(parts[0]) @ embed(parts[1]))
        quality['segment_similarity'] = round(consistency, 4)
        if consistency < 0.45:
            raise AudioError('Speech segments are inconsistent. Use one speaker in a quiet room.')
    return audio, vector, quality


def enroll(samples: list[bytes], authorize=None):
    vectors, qualities = [], []
    for sample in samples:
        _, vector, quality = extract(sample)
        vectors.append(vector)
        qualities.append(quality)
    for first in vectors:
        for second in vectors:
            if float(first @ second) < settings.voice_threshold-settings.voice_margin:
                raise AudioError('Enrollment samples do not consistently match. Record the same speaker three times.')
    template = np.mean(vectors, axis=0)
    template /= np.linalg.norm(template)
    protected = cipher.encrypt(json.dumps(template.tolist()).encode())
    import time
    with db.connect() as connection:
        if authorize:
            authorize()
        connection.execute('DELETE FROM voice_enrollments')
        connection.execute('INSERT INTO voice_enrollments VALUES (1,?,?,?,?)', (protected, len(samples), time.time(), MODEL_NAME))
        connection.execute('INSERT INTO voice_template_metadata VALUES (1,?,?)', (len(template), settings.voice_threshold))
        connection.execute("UPDATE sessions SET speaker_status='UNCERTAIN',pin_until=0,similarity=NULL,last_voice_at=0")
    return {'enrolled': True, 'sample_count': len(samples), 'quality': qualities}


def verify(raw):
    audio, vector, quality = extract(raw)
    row = db.one('SELECT template FROM voice_enrollments WHERE id=1')
    if not row:
        return audio, {'speaker_status': 'UNKNOWN_SPEAKER', 'similarity': None, 'quality': quality, 'reason': 'NO_ENROLLMENT'}
    try:
        template = np.array(json.loads(cipher.decrypt(row['template'])), dtype=np.float32)
        score = float(template @ vector)
    except Exception as exc:
        raise AudioError('Enrollment template is unavailable. Re-enroll after independent verification.') from exc
    status = 'OWNER_CANDIDATE' if score >= settings.voice_threshold else (
        'UNCERTAIN' if score >= settings.voice_threshold-settings.voice_margin else 'UNKNOWN_SPEAKER')
    return audio, {'speaker_status': status, 'similarity': round(score, 4), 'quality': quality, 'reason': 'MODEL_COSINE_SIMILARITY'}
