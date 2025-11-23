"""
Comprehensive edge case and exceptional condition tests for the audio processing system.
Tests corner cases that could cause system failures or unexpected behavior.
"""

import pytest
import numpy as np
import scipy.io.wavfile as wav
import os
import json
from unittest.mock import patch, MagicMock
import urllib.request
import urllib.error

# Set mock credentials before importing lambda_function
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

from moto import mock_aws
import boto3
from audio_processor import AudioProcessor, VoiceDetector
from lambda_function import lambda_handler, post_results


class TestAudioProcessorEdgeCases:
    """Test edge cases in audio processing logic."""

    @pytest.fixture
    def audio_processor(self):
        return AudioProcessor()

    def create_wav_file(self, filename, rate, data):
        """Helper to create WAV files."""
        wav.write(filename, rate, data)
        return filename

    def test_corrupted_wav_file(self, audio_processor, tmp_path):
        """Test handling of corrupted WAV files."""
        filepath = os.path.join(tmp_path, "corrupted.wav")
        # Write random bytes that don't form a valid WAV
        with open(filepath, "wb") as f:
            f.write(b"This is not a valid WAV file content")

        result = audio_processor.process_audio(filepath)
        # Should return safe defaults instead of crashing
        assert result["has_sound"] is False
        assert result["is_speech"] is False
        assert result["is_clapping"] is False
        assert result["confidence"] == 0.0

    def test_empty_file(self, audio_processor, tmp_path):
        """Test handling of empty (0 byte) files."""
        filepath = os.path.join(tmp_path, "empty.wav")
        # Create an empty file
        open(filepath, "w").close()

        result = audio_processor.process_audio(filepath)
        assert result["has_sound"] is False
        assert result["is_speech"] is False
        assert result["is_clapping"] is False
        assert result["confidence"] == 0.0

    def test_nonexistent_file(self, audio_processor):
        """Test handling of nonexistent files."""
        result = audio_processor.process_audio("/path/that/does/not/exist.wav")
        assert result["has_sound"] is False
        assert result["is_speech"] is False
        assert result["is_clapping"] is False
        assert result["confidence"] == 0.0

    def test_very_short_audio(self, audio_processor, tmp_path):
        """Test audio shorter than 1 second."""
        rate = 44100
        # Only 100 samples (~2ms)
        data = (np.sin(2 * np.pi * 440 * np.linspace(0, 0.002, 100)) * 32767).astype(
            np.int16
        )

        filepath = os.path.join(tmp_path, "very_short.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        # Should still process without crashing
        assert isinstance(result["has_sound"], bool)
        assert isinstance(result["is_speech"], bool)
        assert isinstance(result["is_clapping"], bool)
        assert isinstance(result["confidence"], float)

    def test_different_sample_rates(self, audio_processor, tmp_path):
        """Test audio with various sample rates."""
        sample_rates = [8000, 16000, 22050, 48000, 96000]

        for rate in sample_rates:
            t = np.linspace(0, 1, rate)
            data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

            filepath = os.path.join(tmp_path, f"audio_{rate}hz.wav")
            self.create_wav_file(filepath, rate, data)

            result = audio_processor.process_audio(filepath)
            # Should process all sample rates
            assert isinstance(result["has_sound"], bool)
            assert result["has_sound"] is True  # All have sound

    def test_stereo_audio(self, audio_processor, tmp_path):
        """Test stereo (2-channel) audio files."""
        rate = 44100
        t = np.linspace(0, 1, rate)
        # Create stereo data (2 channels)
        left = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        right = (np.sin(2 * np.pi * 880 * t) * 32767).astype(np.int16)
        stereo_data = np.column_stack((left, right))

        filepath = os.path.join(tmp_path, "stereo.wav")
        self.create_wav_file(filepath, rate, stereo_data)

        result = audio_processor.process_audio(filepath)
        # Should handle stereo audio
        assert isinstance(result["has_sound"], bool)

    def test_8bit_audio(self, audio_processor, tmp_path):
        """Test 8-bit audio files."""
        rate = 44100
        t = np.linspace(0, 1, rate)
        # 8-bit audio uses uint8 (0-255)
        data = ((np.sin(2 * np.pi * 440 * t) + 1) * 127.5).astype(np.uint8)

        filepath = os.path.join(tmp_path, "8bit.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert isinstance(result["has_sound"], bool)

    def test_32bit_float_audio(self, audio_processor, tmp_path):
        """Test 32-bit float audio files."""
        rate = 44100
        t = np.linspace(0, 1, rate)
        # 32-bit float audio uses float32 (-1.0 to 1.0)
        data = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        filepath = os.path.join(tmp_path, "32bit_float.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert isinstance(result["has_sound"], bool)

    def test_clipping_audio(self, audio_processor, tmp_path):
        """Test audio with clipping (values at max amplitude)."""
        rate = 44100
        # Create clipped audio (constant max value)
        data = np.full(rate, 32767, dtype=np.int16)

        filepath = os.path.join(tmp_path, "clipping.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert result["has_sound"] is True
        # Should not crash on clipped audio

    def test_near_zero_amplitude(self, audio_processor, tmp_path):
        """Test audio with extremely low amplitude."""
        rate = 44100
        t = np.linspace(0, 1, rate)
        # Very quiet sine wave
        data = (np.sin(2 * np.pi * 440 * t) * 10).astype(np.int16)

        filepath = os.path.join(tmp_path, "quiet.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        # Should detect as no sound due to low amplitude
        assert result["has_sound"] is False


class TestVoiceDetectorEdgeCases:
    """Test edge cases in voice detection logic."""

    def test_empty_chunk(self):
        """Test processing of empty audio chunks."""
        detector = VoiceDetector()
        result = detector.process_chunk(np.array([]))
        assert result is False

    def test_zero_amplitude_chunk(self):
        """Test chunk with all zeros."""
        detector = VoiceDetector()
        chunk = np.zeros(128, dtype=np.int16)
        result = detector.process_chunk(chunk)
        # Should not crash, should return False
        assert isinstance(result, bool)

    def test_single_sample_chunk(self):
        """Test chunk with only one sample."""
        detector = VoiceDetector()
        chunk = np.array([1000], dtype=np.int16)
        result = detector.process_chunk(chunk)
        assert isinstance(result, bool)

    def test_max_amplitude_chunk(self):
        """Test chunk with maximum amplitude values."""
        detector = VoiceDetector()
        chunk = np.full(128, 32767, dtype=np.int16)
        result = detector.process_chunk(chunk)
        assert isinstance(result, bool)

    def test_alternating_amplitude(self):
        """Test chunk with rapidly alternating amplitude."""
        detector = VoiceDetector()
        chunk = np.array(
            [32767 if i % 2 == 0 else -32767 for i in range(128)], dtype=np.int16
        )
        result = detector.process_chunk(chunk)
        assert isinstance(result, bool)


@mock_aws
class TestLambdaHandlerEdgeCases:
    """Test edge cases in Lambda handler logic."""

    @pytest.fixture(autouse=True)
    def aws_credentials(self, monkeypatch):
        """Mocked AWS Credentials for moto."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    @pytest.fixture
    def s3(self, aws_credentials):
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            yield s3

    def test_missing_event_fields(self, s3, monkeypatch):
        """Test event with missing required fields."""
        monkeypatch.setenv("BUCKET_NAME", "test-bucket")

        # Event missing 's3' field
        event = {"Records": [{"eventTime": "2023-10-27T10:00:00Z"}]}

        # Should handle gracefully and return success with failed count
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200

        # Verify the response body contains failure information
        body = json.loads(response["body"])
        assert body["processed"] == 0
        assert body["failed"] == 1
        assert len(body["failed_files"]) == 1

    def test_empty_records_list(self, s3, monkeypatch):
        """Test event with empty Records list."""
        monkeypatch.setenv("BUCKET_NAME", "test-bucket")

        event = {"Records": []}

        # Should complete without processing anything
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200

    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_multiple_records(self, mock_urlopen, mock_processor_cls, s3, monkeypatch):
        """Test processing multiple records in a single event."""
        mock_processor = MagicMock()
        mock_processor.process_audio.return_value = {
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }
        mock_processor_cls.return_value = mock_processor

        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Upload multiple files
        s3.put_object(Bucket="test-bucket", Key="file1.wav", Body=b"dummy content 1")
        s3.put_object(Bucket="test-bucket", Key="file2.wav", Body=b"dummy content 2")
        s3.put_object(Bucket="test-bucket", Key="file3.wav", Body=b"dummy content 3")

        monkeypatch.setenv("BUCKET_NAME", "test-bucket")

        event = {
            "Records": [
                {
                    "eventTime": "2023-10-27T10:00:00Z",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "file1.wav"},
                    },
                },
                {
                    "eventTime": "2023-10-27T10:00:01Z",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "file2.wav"},
                    },
                },
                {
                    "eventTime": "2023-10-27T10:00:02Z",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "file3.wav"},
                    },
                },
            ]
        }

        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
        # Should have processed all 3 files
        assert mock_processor.process_audio.call_count == 3
        assert mock_urlopen.call_count == 3

    @patch("lambda_function.AudioProcessor")
    def test_s3_download_failure(self, mock_processor_cls, s3, monkeypatch):
        """Test handling of S3 download failures."""
        mock_processor = MagicMock()
        mock_processor_cls.return_value = mock_processor

        monkeypatch.setenv("BUCKET_NAME", "test-bucket")

        # Don't upload the file, so download will fail
        event = {
            "Records": [
                {
                    "eventTime": "2023-10-27T10:00:00Z",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "nonexistent.wav"},
                    },
                }
            ]
        }

        # Should raise exception (as per current implementation)
        with pytest.raises(Exception):
            lambda_handler(event, None)

    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_http_post_network_error(
        self, mock_urlopen, mock_processor_cls, s3, monkeypatch
    ):
        """Test handling of network errors when posting results."""
        mock_processor = MagicMock()
        mock_processor.process_audio.return_value = {
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }
        mock_processor_cls.return_value = mock_processor

        # Simulate network error
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")

        s3.put_object(Bucket="test-bucket", Key="test.wav", Body=b"dummy content")
        monkeypatch.setenv("BUCKET_NAME", "test-bucket")

        event = {
            "Records": [
                {
                    "eventTime": "2023-10-27T10:00:00Z",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test.wav"},
                    },
                }
            ]
        }

        # Should raise exception
        with pytest.raises(urllib.error.URLError):
            lambda_handler(event, None)

    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_http_post_timeout(self, mock_urlopen, mock_processor_cls, s3, monkeypatch):
        """Test handling of HTTP timeout errors."""
        mock_processor = MagicMock()
        mock_processor.process_audio.return_value = {
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }
        mock_processor_cls.return_value = mock_processor

        # Simulate timeout
        mock_urlopen.side_effect = TimeoutError("Request timed out")

        s3.put_object(Bucket="test-bucket", Key="test.wav", Body=b"dummy content")
        monkeypatch.setenv("BUCKET_NAME", "test-bucket")

        event = {
            "Records": [
                {
                    "eventTime": "2023-10-27T10:00:00Z",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test.wav"},
                    },
                }
            ]
        }

        with pytest.raises(TimeoutError):
            lambda_handler(event, None)

    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_http_post_4xx_error(
        self, mock_urlopen, mock_processor_cls, s3, monkeypatch
    ):
        """Test handling of HTTP 4xx errors."""
        mock_processor = MagicMock()
        mock_processor.process_audio.return_value = {
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }
        mock_processor_cls.return_value = mock_processor

        # Simulate 400 Bad Request
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://example.com", 400, "Bad Request", {}, None
        )

        s3.put_object(Bucket="test-bucket", Key="test.wav", Body=b"dummy content")
        monkeypatch.setenv("BUCKET_NAME", "test-bucket")

        event = {
            "Records": [
                {
                    "eventTime": "2023-10-27T10:00:00Z",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test.wav"},
                    },
                }
            ]
        }

        with pytest.raises(urllib.error.HTTPError):
            lambda_handler(event, None)

    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_http_post_5xx_error(
        self, mock_urlopen, mock_processor_cls, s3, monkeypatch
    ):
        """Test handling of HTTP 5xx errors."""
        mock_processor = MagicMock()
        mock_processor.process_audio.return_value = {
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }
        mock_processor_cls.return_value = mock_processor

        # Simulate 500 Internal Server Error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://example.com", 500, "Internal Server Error", {}, None
        )

        s3.put_object(Bucket="test-bucket", Key="test.wav", Body=b"dummy content")
        monkeypatch.setenv("BUCKET_NAME", "test-bucket")

        event = {
            "Records": [
                {
                    "eventTime": "2023-10-27T10:00:00Z",
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test.wav"},
                    },
                }
            ]
        }

        with pytest.raises(urllib.error.HTTPError):
            lambda_handler(event, None)


class TestPostResultsEdgeCases:
    """Test edge cases in the post_results function."""

    @patch("urllib.request.urlopen")
    def test_missing_required_fields(self, mock_urlopen):
        """Test posting with missing required fields."""
        # Missing 'confidence' field
        incomplete_data = {
            "filename": "test.wav",
            "timestamp": "2023-10-27T10:00:00Z",
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
        }

        with pytest.raises(KeyError):
            post_results(incomplete_data)

    @patch("urllib.request.urlopen")
    def test_invalid_data_types(self, mock_urlopen):
        """Test posting with invalid data types."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # String instead of boolean
        data = {
            "filename": "test.wav",
            "timestamp": "2023-10-27T10:00:00Z",
            "has_sound": "true",  # String instead of bool
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }

        # Should convert to proper types
        status = post_results(data)
        assert status == 200

        # Verify the posted data has correct types
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        payload = json.loads(req.data)
        assert isinstance(payload["has_sound"], bool)

    @patch("urllib.request.urlopen")
    def test_confidence_out_of_range(self, mock_urlopen):
        """Test posting with confidence values outside 0-1 range."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Confidence > 1
        data = {
            "filename": "test.wav",
            "timestamp": "2023-10-27T10:00:00Z",
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 1.5,  # Out of range
        }

        # Should still post (validation is caller's responsibility)
        status = post_results(data)
        assert status == 200
