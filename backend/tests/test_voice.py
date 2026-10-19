import io
import numpy as np
import soundfile as sf
import pytest
from backend.app.voice import preprocess, AudioError


def wav(samples, rate=16000):
    buffer = io.BytesIO()
    sf.write(buffer, samples, rate, format='WAV', subtype='PCM_16')
    return buffer.getvalue()


@pytest.mark.parametrize('raw', [b'', b'invalid', wav(np.zeros(16000*4)), wav(np.zeros(16000)), wav(np.ones(16000*4))], ids=['empty', 'invalid', 'silent', 'short', 'clipped'])
def test_bad_audio_fails_closed(raw):
    with pytest.raises(AudioError):
        preprocess(raw)
