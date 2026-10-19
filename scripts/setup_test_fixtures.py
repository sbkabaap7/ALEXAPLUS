"""Public SpeechBrain examples used solely as explicit automated test inputs."""
from huggingface_hub import hf_hub_download
for filename in ('example1.wav', 'example2.flac'):
    hf_hub_download('speechbrain/spkrec-ecapa-voxceleb', filename, local_dir='models/test-fixtures')
print('Public test fixtures available. These are not owner enrollment recordings.')
