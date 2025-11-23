import os
import pytest
from audio_processor import AudioProcessor

# Directory containing real sample wav files
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")


def load_sample(filename: str):
    """Helper to get full path to a sample wav file."""
    return os.path.join(SAMPLES_DIR, filename)


class TestAudioProcessorWithRealSamples:
    """Tests using real wav files to verify true/false positives/negatives.

    - clapping.wav: contains clapping sounds → should be detected as sound and clapping.
    - knocking.wav: contains knocking (treated as speech-like sound) → should be detected as sound but not clapping.
    - no-sound.wav: silent audio → should be detected as no sound.
    """

    @pytest.fixture
    def processor(self):
        return AudioProcessor()

    def test_clapping_true_positive(self, processor):
        filepath = load_sample("clapping.wav")
        result = processor.process_audio(filepath)
        assert result["has_sound"] is True
        assert result["is_clapping"] is True
        # Speech detection may also be true, but clapping is the key indicator
        assert isinstance(result["is_speech"], bool)
        assert isinstance(result["confidence"], float)

    def test_knocking_true_positive(self, processor):
        filepath = load_sample("knocking.wav")
        result = processor.process_audio(filepath)
        assert result["has_sound"] is True
        # Not clapping, should be false
        assert result["is_clapping"] is False
        # Speech detection may be true for knocking-like patterns
        assert isinstance(result["is_speech"], bool)
        assert isinstance(result["confidence"], float)

    def test_no_sound_false_negative(self, processor):
        filepath = load_sample("no-sound.wav")
        result = processor.process_audio(filepath)
        # Should correctly identify no sound
        assert result["has_sound"] is False
        # All other flags should be false
        assert result["is_speech"] is False
        assert result["is_clapping"] is False
        assert isinstance(result["confidence"], float)

    def test_speech_true_positive(self, processor):
        filepath = load_sample("speech.wav")
        result = processor.process_audio(filepath)
        assert result["has_sound"] is True
        assert result["is_speech"] is True
        assert result["is_voice"] is True
        assert result["is_clapping"] is False
        assert isinstance(result["confidence"], float)
