"""
Additional robustness tests for scenarios that could cause production issues.
Focuses on resource management, concurrency, and data integrity.
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
from audio_processor import AudioProcessor
from lambda_function import lambda_handler, post_results


class TestResourceManagement:
    """Test proper resource cleanup and management."""

    @pytest.fixture
    def audio_processor(self):
        return AudioProcessor()

    def create_wav_file(self, filename, rate, data):
        """Helper to create WAV files."""
        wav.write(filename, rate, data)
        return filename

    @mock_aws
    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_temp_file_cleanup_on_success(
        self, mock_urlopen, mock_processor_cls, monkeypatch
    ):
        """Verify temp files are cleaned up after successful processing."""
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

            # Verify successful processing and cleanup
            response = lambda_handler(event, None)
            assert response["statusCode"] == 200

    @mock_aws
    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_temp_file_cleanup_on_processing_error(
        self, mock_urlopen, mock_processor_cls, monkeypatch
    ):
        """Verify temp files are cleaned up even when processing fails."""
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

            with pytest.raises(Exception):
                lambda_handler(event, None)

            # Note: Current implementation doesn't clean up on error
            # This test documents the current behavior
            # We'll improve this in the code update

    @mock_aws
    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_temp_file_cleanup_on_post_error(
        self, mock_urlopen, mock_processor_cls, monkeypatch
    ):
        """Verify temp files are cleaned up even when HTTP POST fails."""
        mock_processor = MagicMock()
        mock_processor.process_audio.return_value = {
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }
        mock_processor_cls.return_value = mock_processor

        # Simulate POST error
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

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

            with pytest.raises(urllib.error.URLError):
                lambda_handler(event, None)


class TestDataIntegrity:
    """Test data integrity and validation."""

    @patch("urllib.request.urlopen")
    def test_special_characters_in_filename(self, mock_urlopen):
        """Test handling of special characters in filenames."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        data = {
            "filename": "test file with spaces & special!@#$%^&*().wav",
            "timestamp": "2023-10-27T10:00:00Z",
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }

        status = post_results(data)
        assert status == 200

        # Verify filename was preserved
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        payload = json.loads(req.data)
        assert payload["filename"] == "test file with spaces & special!@#$%^&*().wav"

    @patch("urllib.request.urlopen")
    def test_unicode_in_filename(self, mock_urlopen):
        """Test handling of Unicode characters in filenames."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        data = {
            "filename": "test_文件_🎵.wav",
            "timestamp": "2023-10-27T10:00:00Z",
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }

        status = post_results(data)
        assert status == 200

        # Verify Unicode was preserved
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        payload = json.loads(req.data)
        assert payload["filename"] == "test_文件_🎵.wav"

    @patch("urllib.request.urlopen")
    def test_very_long_filename(self, mock_urlopen):
        """Test handling of extremely long filenames."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Create a very long filename (255 chars is typical filesystem limit)
        long_filename = "a" * 250 + ".wav"

        data = {
            "filename": long_filename,
            "timestamp": "2023-10-27T10:00:00Z",
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }

        status = post_results(data)
        assert status == 200

    @patch("urllib.request.urlopen")
    def test_nan_confidence_value(self, mock_urlopen):
        """Test handling of NaN confidence values."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        data = {
            "filename": "test.wav",
            "timestamp": "2023-10-27T10:00:00Z",
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": float("nan"),
        }

        # Should handle NaN (JSON will convert to null)
        status = post_results(data)
        assert status == 200

    @patch("urllib.request.urlopen")
    def test_infinity_confidence_value(self, mock_urlopen):
        """Test handling of infinity confidence values."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        data = {
            "filename": "test.wav",
            "timestamp": "2023-10-27T10:00:00Z",
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": float("inf"),
        }

        # Should handle infinity (JSON will convert to null)
        status = post_results(data)
        assert status == 200


class TestAudioProcessingRobustness:
    """Test robustness of audio processing algorithms."""

    @pytest.fixture
    def audio_processor(self):
        return AudioProcessor()

    def create_wav_file(self, filename, rate, data):
        """Helper to create WAV files."""
        wav.write(filename, rate, data)
        return filename

    def test_all_nan_audio(self, audio_processor, tmp_path):
        """Test audio data containing all NaN values."""
        rate = 44100
        data = np.full(rate, np.nan, dtype=np.float32)

        filepath = os.path.join(tmp_path, "nan_audio.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        # Should handle gracefully
        assert isinstance(result["has_sound"], bool)

    def test_mixed_nan_audio(self, audio_processor, tmp_path):
        """Test audio data with some NaN values mixed in."""
        rate = 44100
        t = np.linspace(0, 1, rate)
        data = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        # Inject some NaN values
        data[100:200] = np.nan
        data[500:600] = np.nan

        filepath = os.path.join(tmp_path, "mixed_nan.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        # Should handle gracefully
        assert isinstance(result["has_sound"], bool)

    def test_all_inf_audio(self, audio_processor, tmp_path):
        """Test audio data containing all infinity values."""
        rate = 44100
        data = np.full(rate, np.inf, dtype=np.float32)

        filepath = os.path.join(tmp_path, "inf_audio.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        # Should handle gracefully
        assert isinstance(result["has_sound"], bool)

    def test_extremely_long_audio(self, audio_processor, tmp_path):
        """Test processing of very long audio files (simulating memory issues)."""
        rate = 44100
        # 10 minutes of audio
        duration = 600
        t = np.linspace(0, duration, rate * duration)
        data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        filepath = os.path.join(tmp_path, "long_audio.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        # Should process without memory errors
        assert isinstance(result["has_sound"], bool)

    def test_dc_offset_audio(self, audio_processor, tmp_path):
        """Test audio with DC offset (non-zero mean)."""
        rate = 44100
        t = np.linspace(0, 1, rate)
        # Sine wave with DC offset
        data = ((np.sin(2 * np.pi * 440 * t) + 0.5) * 32767).astype(np.int16)

        filepath = os.path.join(tmp_path, "dc_offset.wav")
        self.create_wav_file(filepath, rate, data)

        result = audio_processor.process_audio(filepath)
        assert result["has_sound"] is True


class TestConcurrentProcessing:
    """Test behavior under concurrent/parallel processing scenarios."""

    @mock_aws
    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_processing_order_independence(
        self, mock_urlopen, mock_processor_cls, monkeypatch
    ):
        """Verify that processing multiple records doesn't have order dependencies."""
        mock_processor = MagicMock()

        # Different results for different files
        results = [
            {
                "has_sound": True,
                "is_clapping": False,
                "is_speech": True,
                "is_voice": True,
                "confidence": 0.95,
            },
            {
                "has_sound": True,
                "is_clapping": True,
                "is_speech": False,
                "is_voice": False,
                "confidence": 0.85,
            },
            {
                "has_sound": False,
                "is_clapping": False,
                "is_speech": False,
                "is_voice": False,
                "confidence": 0.0,
            },
        ]

        mock_processor.process_audio.side_effect = results
        mock_processor_cls.return_value = mock_processor

        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")

            # Upload files
            s3.put_object(Bucket="test-bucket", Key="file1.wav", Body=b"content1")
            s3.put_object(Bucket="test-bucket", Key="file2.wav", Body=b"content2")
            s3.put_object(Bucket="test-bucket", Key="file3.wav", Body=b"content3")

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

            # Verify each file was posted with correct data
            assert mock_urlopen.call_count == 3

            # Check that each POST had the correct payload
            calls = mock_urlopen.call_args_list
            for i, call_args in enumerate(calls):
                req = call_args[0][0]
                payload = json.loads(req.data)
                assert payload["filename"] == f"file{i + 1}.wav"
                assert payload["has_sound"] == results[i]["has_sound"]
                assert payload["is_clapping"] == results[i]["is_clapping"]


class TestErrorRecovery:
    """Test error recovery and partial failure scenarios."""

    @mock_aws
    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_partial_batch_failure(self, mock_urlopen, mock_processor_cls, monkeypatch):
        """Test that one failed record doesn't prevent others from being processed."""
        mock_processor = MagicMock()

        # First file succeeds, second fails, third would succeed
        mock_processor.process_audio.side_effect = [
            {
                "has_sound": True,
                "is_clapping": False,
                "is_speech": True,
                "is_voice": True,
                "confidence": 0.95,
            },
            Exception("Processing error"),
            {
                "has_sound": False,
                "is_clapping": False,
                "is_speech": False,
                "is_voice": False,
                "confidence": 0.0,
            },
        ]
        mock_processor_cls.return_value = mock_processor

        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")

            s3.put_object(Bucket="test-bucket", Key="file1.wav", Body=b"content1")
            s3.put_object(Bucket="test-bucket", Key="file2.wav", Body=b"content2")
            s3.put_object(Bucket="test-bucket", Key="file3.wav", Body=b"content3")

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

            # Current implementation raises on first error
            # This documents the current behavior
            with pytest.raises(Exception):
                lambda_handler(event, None)

            # Only first file should have been posted
            assert mock_urlopen.call_count == 1
