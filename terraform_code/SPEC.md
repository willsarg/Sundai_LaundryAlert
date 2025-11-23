# Sound Classifier Specification

## 1. Overview
This document outlines the technical specification for the Sound Classifier component of the Sundai Laundry Alert system. The system processes audio clips from a hardware device to detect and classify specific sound patterns (general sound and knocking). Long term, this will be used to determine washing machine status.

## 2. Architecture
The system follows a serverless event-driven architecture:
1.  **Ingestion**: Audio files (WAV) are uploaded to an S3 bucket.
2.  **Trigger**: S3 Event Notifications trigger an AWS Lambda function.
3.  **Processing**: The Lambda function (Python) downloads the file, analyzes it, and determines sound characteristics.
4.  **Persistence**: Classification results are posted to a public HTTP endpoint.
5.  **Cleanup**: Source audio files are deleted via S3 Lifecycle Policy to maintain hygiene.

## 3. Infrastructure
*   **IaC**: Terraform (existing `terraform_code` directory).
*   **Compute**: AWS Lambda (`laundry-alert-processor`).
    *   Runtime: Python 3.14
    *   Memory: TBD (Start with 128MB, scale if signal processing requires more).
    *   Timeout: 30s (per `lambda.tf`).
*   **Storage**: AWS S3 (`sundai-laundry-alert-${var.region}`).
*   **Storage**: AWS S3 (`sundai-laundry-alert-${var.region}`).
*   **Reporting**: Public HTTP Endpoint.

## 4. Input Specifications
*   **Format**: WAV audio files.
*   **Duration**: ~10 seconds per clip.
*   **Throughput**: ~6 files per minute (steady state).
*   **Retention**: S3 Lifecycle Policy to expire objects older than 5 minutes.

## 5. Classification Logic
The classifier will use signal processing techniques (e.g., `scipy`, `numpy`) to determine:

### 5.1. Sound / No Sound
*   **Method**: Amplitude thresholding / RMS (Root Mean Square) energy calculation.
*   **Logic**: If the average energy of the clip exceeds a defined threshold (noise floor), it is classified as `has_sound = True`.

### 5.2. Clapping / No Clapping
*   **Method**: Peak detection and rhythmic analysis.
*   **Logic**: Identify sharp, transient peaks in the audio signal. Analyze the interval between peaks to detect rhythmic patterns.
*   **Output**: `is_clapping = True/False`, `confidence = 0.0 - 1.0`.

## 6. Data Reporting (HTTP Endpoint)
**Endpoint**: `https://main.do3lhk8wdr8hy.amplifyapp.com/api/laundry-events`
**Method**: `POST`
**Content-Type**: `application/json`

The Lambda will post the following schema to the endpoint:

```json
{
  "filename": "machine_1_1698400000.wav",
  "timestamp": "2023-10-27T10:00:00Z",
  "has_sound": true,
  "is_clapping": false,
  "is_speech": true,
  "is_voice": true,
  "confidence": 0.95
}
```

## 7. Development Guidelines
*   **Language**: Python 3.14
*   **Style**: PEP 8 compliant.
*   **Best Practices**:
    *   Use `boto3` for AWS interactions.
    *   Handle exceptions gracefully (e.g., corrupt audio files).
    *   Structured logging (JSON format preferred) for CloudWatch.

## 8. Testing Strategy
Automated testing is a priority to ensure velocity.

### 8.1. Unit Tests
*   **Framework**: `pytest`.
*   **Scope**:
    *   Test classification logic with sample WAV files (fixtures).
    *   Test edge cases (silent files, white noise, corrupt files).

### 8.2. Integration Tests
*   **Tools**: `moto` (for mocking AWS services).
*   **Scope**:
    *   Mock S3 `ObjectCreated` event.
    *   Verify Lambda handler correctly parses the event.
    *   Verify file download from mocked S3.
    *   Verify HTTP POST request to endpoint.
    *   Verify source file deletion logic.

## 9. Deployment
*   **Packaging**: Docker container or Zip with Lambda Layers (if dependencies like `scipy` exceed size limits).
*   **CI/CD**: (Future scope) Automated deployment via GitHub Actions.
