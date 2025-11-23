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


def post_results(data, max_retries=3):
    """
    Post classification results to the HTTP endpoint with retry logic.

    Args:
        data: Dictionary containing classification results
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        HTTP status code

    Raises:
        urllib.error.URLError: If all retry attempts fail
    """
    url = "https://main.do3lhk8wdr8hy.amplifyapp.com/api/laundry-events"
    headers = {"Content-Type": "application/json"}

    # Ensure data types are JSON serializable and handle special float values
    confidence = float(data["confidence"])

    # Handle NaN and Inf values by converting to 0.0
    if not (confidence == confidence):  # NaN check
        print("Warning: NaN confidence value detected, converting to 0.0")
        confidence = 0.0
    elif confidence == float("inf") or confidence == float("-inf"):
        print("Warning: Infinite confidence value detected, converting to 0.0")
        confidence = 0.0

    # Clamp confidence to valid range [0.0, 1.0]
    confidence = max(0.0, min(1.0, confidence))

    payload = {
        "filename": data["filename"],
        "timestamp": data["timestamp"],
        "has_sound": bool(data["has_sound"]),
        "is_clapping": bool(data["is_clapping"]),
        "is_speech": bool(data["is_speech"]),
        "is_voice": bool(data["is_voice"]),
        "confidence": confidence,
    }

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )

    last_exception = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                print(f"Posted results. Status: {response.status}")
                return response.status
        except urllib.error.HTTPError as e:
            # Don't retry on 4xx errors (client errors)
            if 400 <= e.code < 500:
                print(
                    f"HTTP {e.code} error posting results (client error, not retrying): {e}"
                )
                raise e
            # Retry on 5xx errors (server errors)
            last_exception = e
            print(
                f"HTTP {e.code} error posting results (attempt {attempt + 1}/{max_retries}): {e}"
            )
        except (urllib.error.URLError, TimeoutError) as e:
            last_exception = e
            print(
                f"Network error posting results (attempt {attempt + 1}/{max_retries}): {e}"
            )

        # Exponential backoff before retry (except on last attempt)
        if attempt < max_retries - 1:
            import time

            backoff_time = 2**attempt  # 1s, 2s, 4s
            print(f"Retrying in {backoff_time} seconds...")
            time.sleep(backoff_time)

    # All retries failed
    print(f"Failed to post results after {max_retries} attempts")
    raise last_exception


def lambda_handler(event, context):
    """
    Lambda function triggered by S3 ObjectCreated events.
    Processes audio files and posts classification results to HTTP endpoint.

    Features:
    - Robust error handling with proper resource cleanup
    - Retry logic for HTTP POST failures
    - Detailed logging for debugging
    - Graceful handling of malformed events
    """
    print(f"Received event: {json.dumps(event)}")

    s3 = get_s3_client()
    processor = AudioProcessor()

    # Track processing results
    processed_count = 0
    failed_count = 0
    failed_files = []

    for record in event["Records"]:
        download_path = None

        try:
            # Extract S3 information
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]
            event_time = record.get("eventTime", "")

            print(f"Processing file: s3://{bucket}/{key}")

            # Download file to /tmp with unique name
            download_path = f"/tmp/{uuid.uuid4()}.wav"
            s3.download_file(bucket, key, download_path)
            print(f"Downloaded to: {download_path}")

            # Process audio
            results = processor.process_audio(download_path)
            print(f"Results for {key}: {results}")

            # Prepare data for POST
            data = {
                "filename": key,
                "timestamp": event_time,
                "has_sound": results["has_sound"],
                "is_clapping": results["is_clapping"],
                "is_speech": results["is_speech"],
                "is_voice": results["is_voice"],
                "confidence": results["confidence"],
            }

            # Post to endpoint with retry logic
            post_results(data)
            processed_count += 1
            print(f"Successfully processed: {key}")

        except KeyError as e:
            # Handle malformed event records
            error_msg = f"Malformed event record, missing field: {e}"
            print(f"ERROR: {error_msg}")
            failed_count += 1
            failed_files.append(
                {
                    "file": record.get("s3", {})
                    .get("object", {})
                    .get("key", "unknown"),
                    "error": error_msg,
                }
            )
            # Continue processing other records instead of failing entire batch
            continue

        except Exception as e:
            # Log error with full context
            error_msg = f"Error processing {key}: {type(e).__name__}: {str(e)}"
            print(f"ERROR: {error_msg}")
            failed_count += 1
            failed_files.append({"file": key, "error": str(e)})

            # For S3 batch processing, we want to raise to trigger retry
            # But first, ensure cleanup happens
            if download_path and os.path.exists(download_path):
                try:
                    os.remove(download_path)
                    print(f"Cleaned up temp file: {download_path}")
                except Exception as cleanup_error:
                    print(
                        f"Warning: Failed to cleanup temp file {download_path}: {cleanup_error}"
                    )

            # Re-raise to trigger Lambda retry mechanism
            raise e

        finally:
            # Always cleanup temp files
            if download_path and os.path.exists(download_path):
                try:
                    os.remove(download_path)
                    print(f"Cleaned up temp file: {download_path}")
                except Exception as cleanup_error:
                    print(
                        f"Warning: Failed to cleanup temp file {download_path}: {cleanup_error}"
                    )

    # Log summary
    print(f"Processing complete. Processed: {processed_count}, Failed: {failed_count}")
    if failed_files:
        print(f"Failed files: {json.dumps(failed_files)}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Processing complete",
                "processed": processed_count,
                "failed": failed_count,
                "failed_files": failed_files,
            }
        ),
    }
