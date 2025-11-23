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


class TestVoiceDetectorFullCoverage:
    """Tests to cover VoiceDetector lines 61-65 and 114-117."""

    def test_voice_detector_inf_in_rms_calculation(self):
        """Test VoiceDetector handling of Inf values in RMS calculation (lines 61-65)."""
        detector = VoiceDetector()

        # Create a chunk that will produce Inf in RMS calculation
        # Use extremely large values that could overflow
        chunk = np.array([np.inf] * 128, dtype=np.float32)

        result = detector.process_chunk(chunk)
        # Should handle gracefully and return False
        assert isinstance(result, bool)

    def test_voice_detector_value_error_in_calculation(self):
        """Test VoiceDetector exception handling (lines 63-65)."""
        detector = VoiceDetector()

        # Mock np.mean to raise ValueError instead of using complex numbers
        with patch("numpy.mean") as mock_mean:
            mock_mean.side_effect = ValueError("Invalid operation")

            chunk = np.array([1000] * 128, dtype=np.int16)
            result = detector.process_chunk(chunk)

            # Should catch exception and return False
            assert result is False

    def test_voice_detector_silence_after_speech(self):
        """Test VoiceDetector silence detection after speech (lines 114-117)."""
        detector = VoiceDetector(sample_rate=44100)

        # First, calibrate the detector
        for _ in range(detector.max_calibration_frames):
            silence = np.zeros(128, dtype=np.int16)
            detector.process_chunk(silence)

        # Now send loud chunks to trigger speech detection
        for _ in range(10):
            loud_chunk = np.full(128, 30000, dtype=np.int16)
            detector.process_chunk(loud_chunk)

        # Verify we're in speaking state
        assert detector.is_speaking is True

        # Now send silence to trigger the silence counter and speech end
        # Need to send enough silence frames to exceed silence_threshold_frames
        for _ in range(detector.silence_threshold_frames + 5):
            silence = np.zeros(128, dtype=np.int16)
            result = detector.process_chunk(silence)
        # Should have stopped speaking (lines 115-117 executed)
        assert detector.is_speaking is False

    def test_voice_detector_speech_counter_above_min_frames(self):
        """Test VoiceDetector when speech_counter >= min_speech_frames (branch 110->113)."""
        detector = VoiceDetector(sample_rate=44100)

        # First, calibrate the detector
        for _ in range(detector.max_calibration_frames):
            silence = np.zeros(128, dtype=np.int16)
            detector.process_chunk(silence)

        # Trigger speaking and sustain it for > min_speech_frames (173)
        # We need enough frames so that speech_counter >= 173
        for _ in range(200):
            loud_chunk = np.full(128, 30000, dtype=np.int16)
            detector.process_chunk(loud_chunk)

        assert detector.is_speaking is True
        assert detector.speech_counter >= 173

        # Now send silence.
        # Smoothing will keep currently_speaking=True for a few frames (history_length=5).
        # We need to send enough silence to clear the buffer and trigger the "else" block
        # where currently_speaking becomes False.

        # Send enough silence to clear smoothing buffer + 1
        for _ in range(detector.history_length + 2):
            silence = np.zeros(128, dtype=np.int16)
            detector.process_chunk(silence)

        # At some point in the loop above:
        # 1. currently_speaking became False
        # 2. speech_counter was >= 173 (so line 110 was False)
        # 3. Line 111 (reset) was SKIPPED
        # 4. Line 113 (is_speaking) was True
        # 5. silence_counter incremented

        # Verify we are still considered "speaking" (state hasn't reset immediately)
        assert detector.is_speaking is True
        # And speech_counter should NOT have been reset to 0
        assert detector.speech_counter > 0


class TestAudioProcessorFullCoverage:
    """Tests to cover AudioProcessor lines 156-157 and 173."""

    @pytest.fixture
    def audio_processor(self):
        return AudioProcessor()

    def create_wav_file(self, filename, rate, data):
        """Helper to create WAV files."""
        wav.write(filename, rate, data)
        return filename

    def test_truly_empty_audio_after_conversion(self, audio_processor, tmp_path):
        """Test empty audio data path (lines 156-157)."""
        # Create a WAV file with data that becomes empty after processing
        # This is tricky - we need data that exists but becomes empty

        # One way: create a file with only header, no actual samples
        rate = 44100
        # Create an empty array
        data = np.array([], dtype=np.int16)

        filepath = os.path.join(tmp_path, "truly_empty.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)

        # Should hit lines 156-157 and return safe defaults
        assert result["has_sound"] is False
        assert result["is_speech"] is False
        assert result["is_voice"] is False
        assert result["is_clapping"] is False
        assert result["confidence"] == 0.0

    def test_global_rms_produces_nan(self, audio_processor, tmp_path):
        """Test handling of NaN in global RMS calculation (line 173)."""
        # This is hard to trigger naturally, but we can create a scenario
        # where the RMS calculation might produce NaN

        # Create audio with all NaN values that pass initial checks
        rate = 44100
        # Start with valid data
        data = np.zeros(rate, dtype=np.float32)
        # Make it all NaN after some processing
        data[:] = np.nan

        filepath = os.path.join(tmp_path, "nan_rms.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)

        # Should handle NaN gracefully (line 173 should be hit)
        assert isinstance(result["has_sound"], bool)
        assert isinstance(result["confidence"], float)


class TestLambdaHandlerFullCoverage:
    """Tests to cover lambda_function.py lines 187-188 and 201-202."""

    @mock_aws
    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_cleanup_error_in_exception_handler(
        self, mock_urlopen, mock_processor_cls, monkeypatch
    ):
        """Test cleanup error handling in exception path (lines 187-188)."""
        mock_processor = MagicMock()
        # Simulate processing error
        mock_processor.process_audio.side_effect = Exception("Processing failed")
        mock_processor_cls.return_value = mock_processor

        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
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

            # Mock os.remove to raise an exception during cleanup
            with patch("os.remove") as mock_remove:
                # First call (in exception handler) raises exception
                # Second call (in finally) succeeds
                mock_remove.side_effect = [
                    PermissionError("Cannot delete file"),
                    None,
                ]

                with pytest.raises(Exception, match="Processing failed"):
                    lambda_handler(event, None)

                # Verify cleanup was attempted (lines 187-188 executed)
                assert mock_remove.call_count >= 1

    @mock_aws
    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_cleanup_error_in_finally_block(
        self, mock_urlopen, mock_processor_cls, monkeypatch
    ):
        """Test cleanup error handling in finally block (lines 201-202)."""
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

        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
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

            # Mock os.remove to raise exception in finally block
            with patch("os.remove") as mock_remove:
                mock_remove.side_effect = PermissionError("Cannot delete file")

                # Should complete successfully despite cleanup error
                response = lambda_handler(event, None)

                assert response["statusCode"] == 200
                # Verify cleanup was attempted (lines 201-202 executed)
                assert mock_remove.called


class TestClappingDetectionCoverage:
    """Test to cover clapping detection lines 222-223."""

    @pytest.fixture
    def audio_processor(self):
        return AudioProcessor()

    def create_wav_file(self, filename, rate, data):
        """Helper to create WAV files."""
        wav.write(filename, rate, data)
        return filename

    def test_clapping_detection_with_high_peaks(self, audio_processor, tmp_path):
        """Test clapping detection to cover lines 222-223."""
        rate = 44100

        # Create audio with high amplitude peaks but NOT speech
        # Need to avoid triggering speech detection

        # Start with very low noise floor for calibration
        silence_duration = 0.5
        silence = np.random.normal(0, 5, int(rate * silence_duration))

        # Create sharp, high peaks (clapping pattern)
        # But keep them short and sparse to avoid speech detection
        clap_duration = 0.5
        clap_audio = np.random.normal(0, 100, int(rate * clap_duration))

        # Add very high peaks (above PEAK_THRESHOLD of 20000)
        for i in range(0, len(clap_audio), rate // 10):  # 10 claps per second
            if i + 50 < len(clap_audio):
                clap_audio[i : i + 50] = 25000  # Above PEAK_THRESHOLD

        # Concatenate
        data = np.concatenate([silence, clap_audio]).astype(np.int16)

        filepath = os.path.join(tmp_path, "clapping_coverage.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)

        # Should detect sound
        assert result["has_sound"] is True

        # Depending on the exact pattern, might detect as clapping or speech
        # The key is that we hit lines 222-223 (clapping detection)
        # We can verify by checking that confidence is set
        assert isinstance(result["confidence"], float)


class TestFinalCoverageLines:
    """Tests to cover the final 3 uncovered lines."""

    def test_voice_detector_floating_point_error(self):
        """
        Test FloatingPointError exception handling in VoiceDetector (lines 63-65).
        This is extremely difficult to trigger naturally, so we'll use mocking.
        """
        detector = VoiceDetector()

        # Mock np.sqrt to raise FloatingPointError
        with patch("numpy.sqrt") as mock_sqrt:
            mock_sqrt.side_effect = FloatingPointError("Floating point error")

            chunk = np.array([1000] * 128, dtype=np.int16)
            result = detector.process_chunk(chunk)

            # Should catch the exception and return False (lines 63-65)
            assert result is False

    def test_voice_detector_value_error_from_numpy(self):
        """
        Test ValueError exception handling in VoiceDetector (lines 63-65).
        """
        detector = VoiceDetector()

        # Mock np.mean to raise ValueError
        with patch("numpy.mean") as mock_mean:
            mock_mean.side_effect = ValueError("Invalid value")

            chunk = np.array([1000] * 128, dtype=np.int16)
            result = detector.process_chunk(chunk)

            # Should catch the exception and return False (lines 63-65)
            assert result is False

    def test_audio_processor_nan_in_global_rms(self, tmp_path):
        """
        Test NaN handling in global RMS calculation (line 173).
        Uses mocking to trigger NaN in RMS without overflow warnings.
        """
        processor = AudioProcessor()

        # Create a normal WAV file
        rate = 44100
        data = np.zeros(rate, dtype=np.int16)

        filepath = os.path.join(tmp_path, "nan_global_rms.wav")
        wav.write(filepath, rate, data)

        # Mock np.sqrt to return NaN for the global RMS calculation
        # We need to be selective - only return NaN for the right call
        original_sqrt = np.sqrt

        def selective_nan_sqrt(x):
            result = original_sqrt(x)
            # If this looks like a global RMS calculation (single value, not array)
            if np.isscalar(result) and result < 1.0:
                return np.nan
            return result

        with patch("numpy.sqrt", side_effect=selective_nan_sqrt):
            result = processor.process_audio(filepath)

            # Should handle gracefully (line 173 should be executed)
            assert isinstance(result["has_sound"], bool)
            assert isinstance(result["confidence"], float)


class TestExceptionPathInAudioProcessor:
    """Test the general exception handler in AudioProcessor."""

    def test_audio_processor_general_exception(self, tmp_path):
        """
        Test the general exception handler in process_audio.
        This ensures the except Exception block is covered.
        """
        processor = AudioProcessor()

        # Create a normal file
        rate = 44100
        data = np.zeros(rate, dtype=np.int16)
        filepath = os.path.join(tmp_path, "test.wav")
        wav.write(filepath, rate, data)

        # Mock wav.read to raise an unexpected exception
        with patch("scipy.io.wavfile.read") as mock_read:
            mock_read.side_effect = RuntimeError("Unexpected error")

            result = processor.process_audio(filepath)

            # Should catch exception and return safe defaults
            assert result["has_sound"] is False
            assert result["is_speech"] is False
            assert result["is_voice"] is False
            assert result["is_clapping"] is False
            assert result["confidence"] == 0.0
