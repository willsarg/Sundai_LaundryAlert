import pytest
import numpy as np
import scipy.io.wavfile as wav
import os
from audio_processor import AudioProcessor


class TestAudioProcessor:
    @pytest.fixture
    def audio_processor(self):
        return AudioProcessor()

    def create_wav_file(self, filename, rate, data):
        wav.write(filename, rate, data)
        return filename

    def test_has_sound_true(self, audio_processor, tmp_path):
        # Generate a sine wave (sound)
        rate = 44100
        t = np.linspace(0, 1, rate)
        data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        filepath = os.path.join(tmp_path, "sound.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert result["has_sound"] is True

    def test_has_sound_false(self, audio_processor, tmp_path):
        # Generate silence
        rate = 44100
        data = np.zeros(rate, dtype=np.int16)

        filepath = os.path.join(tmp_path, "silence.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert result["has_sound"] is False

    def test_is_knocking_true(self, audio_processor, tmp_path):
        # Generate knocking pattern (transient peaks)
        rate = 44100
        data = np.random.normal(0, 100, rate).astype(np.int16)  # Noise floor

        # Add knocks
        for i in range(0, rate, rate // 4):  # 4 knocks per second
            data[i : i + 100] = 30000

        filepath = os.path.join(tmp_path, "knocking.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert result["is_knocking"] is True
