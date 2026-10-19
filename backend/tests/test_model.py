"""Public fixture validation, not a biometric accuracy benchmark or user enrollment."""
import io
import time
from pathlib import Path
import numpy as np
import soundfile as sf
import pytest
from backend.app import voice
from backend.app.security import db
from backend.app.transcription import transcribe
from backend.app.privacy import voice_transition

FIXTURE = Path('models/test-fixtures/example1.wav')
pytestmark = [pytest.mark.model, pytest.mark.skipif(not FIXTURE.exists() or not voice.model_status()['available'], reason='Run scripts/setup_models and scripts/setup_test_fixtures first')]


def test_real_embedding_enrollment_matching_deletion(session_id):
    raw = FIXTURE.read_bytes()
    audio, vector, quality = voice.extract(raw)
    assert vector.shape == (256,) and np.isclose(vector@vector, 1, atol=1e-5)
    assert quality['speech_seconds'] >= 2
    buffers = [raw]
    # Clearly labeled signal variants exercise three-sample storage, not independent-speaker accuracy.
    for gain in (0.8, 1.2):
        file = io.BytesIO()
        sf.write(file, audio*gain, 16000, format='WAV', subtype='PCM_16')
        buffers.append(file.getvalue())
    result = voice.enroll(buffers)
    assert result['sample_count'] == 3
    row = db.one('SELECT template FROM voice_enrollments')
    assert row['template'].startswith(b'gAAAA')
    _, matched = voice.verify(raw)
    assert matched['speaker_status'] == 'OWNER_CANDIDATE'
    assert matched['similarity'] > 0.9
    second = Path('models/test-fixtures/example2.flac')
    if second.exists():
        waveform, rate = sf.read(second, dtype='float32')
        file = io.BytesIO()
        # Repeat this short public fixture to meet minimum input duration.
        # This is an execution check on two examples, not a population accuracy claim.
        sf.write(file, np.tile(waveform, 2), rate, format='WAV', subtype='PCM_16')
        _, other = voice.verify(file.getvalue())
        assert other['speaker_status'] == 'UNKNOWN_SPEAKER'
    session = db.session(session_id)
    db.update_session(session_id, **voice_transition(session, 'UNKNOWN_SPEAKER'))
    db.update_session(session_id, **voice_transition(db.session(session_id), matched['speaker_status']))
    assert db.session(session_id)['guest_presence'] == 'CLEAR'
    db.execute('DELETE FROM voice_enrollments')
    _, deleted = voice.verify(raw)
    assert deleted['speaker_status'] == 'UNKNOWN_SPEAKER'
    assert not db.one('SELECT * FROM voice_template_metadata')


def test_real_local_transcription():
    if not Path('models/whisper/model.bin').exists():
        pytest.skip('Whisper model not installed')
    audio, _, _ = voice.extract(FIXTURE.read_bytes())
    result = transcribe(audio)
    assert result['available'] and len(result['text']) > 10
