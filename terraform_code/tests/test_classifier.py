import pytest
import numpy as np
import scipy.io.wavfile as wav
import os
import audio_processor as audio_module
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

    def test_is_clapping_true(self, audio_processor, tmp_path):
        # Generate clapping pattern (transient peaks)
        rate = 44100
        data = np.random.normal(0, 100, rate).astype(np.int16)  # Noise floor

        # Add claps (short bursts)
        for i in range(0, rate, rate // 4):  # 4 claps per second
            data[i : i + 100] = 30000

        filepath = os.path.join(tmp_path, "clapping.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert result["has_sound"] is True
        assert result["is_clapping"] is True
        assert result["is_speech"] is False

    def test_is_speech_true(self, audio_processor, tmp_path):
        # Generate speech-like pattern (sustained energy)
        rate = 44100

        # 1. Silence for calibration (0.5 seconds)
        silence_duration = 0.5
        silence = np.random.normal(0, 10, int(rate * silence_duration))

        # 2. Speech signal (3 seconds)
        t = np.linspace(0, 3, rate * 3)  # 3 seconds
        # Carrier
        carrier = np.sin(2 * np.pi * 440 * t)
        # Modulator (to simulate speech envelope)
        modulator = np.abs(np.sin(2 * np.pi * 2 * t))  # 2Hz modulation

        # Combine and scale
        speech_signal = carrier * modulator * 20000

        # Concatenate
        data = np.concatenate([silence, speech_signal]).astype(np.int16)

        # Add some noise floor to everything
        noise = np.random.normal(0, 100, len(data)).astype(np.int16)
        data = data + noise

        filepath = os.path.join(tmp_path, "speech.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert result["has_sound"] is True
        assert result["is_speech"] is True
        assert result["is_voice"] is True
        # Clapping might be false or true depending on peaks, but speech should take precedence in our logic?
        # Actually our logic says if is_speech, we don't check clapping.
        assert result["is_clapping"] is False

    def test_speech_ratio_below_threshold_does_not_flag_speech(
        self, audio_processor, tmp_path, monkeypatch
    ):
        class FakeDetector:
            def __init__(self, sample_rate):
                self.sample_rate = sample_rate
                self.chunk_size = 1
                self.max_calibration_frames = 0
                self._counter = 0

            def process_chunk(self, chunk):
                self._counter += 1
                return self._counter == 1

        monkeypatch.setattr(audio_module, "VoiceDetector", FakeDetector)

        rate = 44100
        # 50 samples with modest amplitude ensure has_sound is True
        data = np.full(50, 200, dtype=np.int16)

        filepath = os.path.join(tmp_path, "low_ratio_speech.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert result["has_sound"] is True
        # Speech is detected in only a tiny fraction of valid frames,
        # so it should not be classified as speech.
        assert result["is_speech"] is False
