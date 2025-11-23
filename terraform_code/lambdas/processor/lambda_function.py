import json
import os
import boto3

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    """
    Lambda function triggered by S3 ObjectCreated events.
    Replace this with your actual processing logic.
    """
    print(f"Received event: {json.dumps(event)}")

    # Get bucket and object info from the event
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        print(f"Processing file: s3://{bucket}/{key}")

        # TODO: Add your processing logic here
        # Example: Download the .wav file
        # response = s3_client.get_object(Bucket=bucket, Key=key)
        # audio_data = response['Body'].read()

        # Process the audio data...

        # Example: Upload results back to S3
        # s3_client.put_object(
        #     Bucket=bucket,
        #     Key=f"processed/{key}",
        #     Body=processed_data
        # )

    return {"statusCode": 200, "body": json.dumps("Processing complete")}
