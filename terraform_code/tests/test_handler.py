import pytest
import boto3
import json
import os
from unittest.mock import patch, MagicMock
import urllib.request

# Set mock credentials before importing lambda_function which initializes boto3 client
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

from moto import mock_aws
from lambda_function import lambda_handler


@mock_aws
class TestLambdaHandler:
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

    @patch("lambda_function.AudioProcessor")
    @patch("urllib.request.urlopen")
    def test_handler_success(self, mock_urlopen, mock_processor_cls, s3, monkeypatch):
        # Mock AudioProcessor
        mock_processor = MagicMock()
        mock_processor.process_audio.return_value = {
            "has_sound": True,
            "is_clapping": False,
            "is_speech": True,
            "is_voice": True,
            "confidence": 0.95,
        }
        mock_processor_cls.return_value = mock_processor

        # Mock urlopen context manager
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Upload a dummy file
        s3.put_object(Bucket="test-bucket", Key="test.wav", Body=b"dummy wav content")

        # Set env vars
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

        # Run handler
        response = lambda_handler(event, None)

        # Verify response
        assert response["statusCode"] == 200

        # Verify AudioProcessor was called
        mock_processor.process_audio.assert_called()

        # Verify HTTP POST
        mock_urlopen.assert_called_once()
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        assert isinstance(req, urllib.request.Request)
        assert (
            req.full_url
            == "https://main.do3lhk8wdr8hy.amplifyapp.com/api/laundry-events"
        )
        assert req.method == "POST"

        # Verify payload
        payload = json.loads(req.data)
        assert payload["filename"] == "test.wav"
        assert payload["timestamp"] == "2023-10-27T10:00:00Z"
        assert payload["has_sound"] is True
        assert payload["is_clapping"] is False
        assert payload["is_speech"] is True
        assert payload["is_voice"] is True
        assert payload["confidence"] == 0.95
