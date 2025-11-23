import json
import os
import boto3
import uuid
import urllib.request
from audio_processor import AudioProcessor

# Lazy initialization
_s3_client = None


def get_s3_client():
    global _s3_client
    if not _s3_client:
        _s3_client = boto3.client("s3")
    return _s3_client


def post_results(data):
    url = "https://main.do3lhk8wdr8hy.amplifyapp.com/api/laundry-events"
    headers = {"Content-Type": "application/json"}

    # Ensure data types are JSON serializable
    # The processor returns native python types, so json.dumps handles them.
    # But just to be safe and match the spec exactly:
    payload = {
        "filename": data["filename"],
        "timestamp": data["timestamp"],
        "has_sound": bool(data["has_sound"]),
        "is_clapping": bool(data["is_clapping"]),
        "is_speech": bool(data["is_speech"]),
        "is_voice": bool(data["is_voice"]),
        "confidence": float(data["confidence"]),
    }

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            print(f"Posted results. Status: {response.status}")
            return response.status
    except urllib.error.URLError as e:
        print(f"Error posting results: {e}")
        raise e


def lambda_handler(event, context):
    """
    Lambda function triggered by S3 ObjectCreated events.
    """
    print(f"Received event: {json.dumps(event)}")

    s3 = get_s3_client()
    processor = AudioProcessor()

    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        print(f"Processing file: s3://{bucket}/{key}")

        try:
            # Download file to /tmp
            download_path = f"/tmp/{uuid.uuid4()}.wav"
            s3.download_file(bucket, key, download_path)

            # Process
            results = processor.process_audio(download_path)
            print(f"Results for {key}: {results}")

            # Prepare data for POST
            data = {
                "filename": key,
                "timestamp": record["eventTime"],
                "has_sound": results["has_sound"],
                "is_clapping": results["is_clapping"],
                "is_speech": results["is_speech"],
                "is_voice": results["is_voice"],
                "confidence": results["confidence"],
            }

            # Post to endpoint
            post_results(data)

            # Cleanup
            if os.path.exists(download_path):
                os.remove(download_path)

        except Exception as e:
            print(f"Error processing {key}: {e}")
            # Continue processing other records? Or raise?
            # For S3 batch, raising causes retry.
            # Let's raise to ensure visibility.
            raise e

    return {"statusCode": 200, "body": json.dumps("Processing complete")}
