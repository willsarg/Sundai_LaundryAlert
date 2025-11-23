import subprocess
import time
import os
import datetime
import sys
import requests

# Configuration
DURATION = 10  # Duration of each recording in seconds
OUTPUT_DIR = "recordings"
DEVICE = "plughw:0,0"  # Default device. Check 'arecord -l' to confirm.
                       # It might be plughw:1,0 if the onboard audio is enabled.

# S3 Configuration
S3_BUCKET_URL = "https://sundai-laundry-alert-us-east-1.s3.us-east-1.amazonaws.com/"

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

def upload_file(filepath):
    """Uploads the recorded file to the S3 bucket."""
    filename = os.path.basename(filepath)
    url = f"{S3_BUCKET_URL}{filename}"
    print(f"Attempting to upload {filepath} to {url}...")
    
    try:
        with open(filepath, 'rb') as f:
            headers = {'Content-Type': 'audio/wav'}
            response = requests.put(url, data=f, headers=headers)
            
        if response.status_code == 200:
            print(f"Successfully uploaded {filepath}")
            # Optional: Delete file after successful upload to save space
            # os.remove(filepath) 
        else:
            print(f"Failed to upload {filepath}. Status code: {response.status_code}")
            print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"Error uploading file: {e}")
        print("Check your internet connection.")

def record_audio():
    ensure_output_dir()
    
    print(f"Starting audio recording service. Recording {DURATION}s chunks to '{OUTPUT_DIR}/'...")
    print(f"Upload target: {S3_BUCKET_URL}")
    
    try:
        while True:
            # Generate filename based on current timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = os.path.join(OUTPUT_DIR, f"recording_{timestamp}.wav")
            
            # Construct the arecord command
            # -D: Device
            # -f: Format (cd quality: 16 bit little endian, 44100Hz, stereo)
            # -d: Duration in seconds
            # -t: File type (wav)
            # -q: Quiet mode (suppress output)
            cmd = [
                "arecord",
                "-D", DEVICE,
                "-f", "cd",
                "-d", str(DURATION),
                "-t", "wav",
                "-q",
                filename
            ]
            
            print(f"Recording: {filename}")
            
            # Run the command and wait for it to finish
            try:
                subprocess.run(cmd, check=True)
                
                # Upload the file immediately after recording
                upload_file(filename)
                
            except subprocess.CalledProcessError as e:
                print(f"Error recording audio: {e}")
                # Wait a bit before retrying to avoid rapid failure loops
                time.sleep(5)
            except FileNotFoundError:
                print("Error: 'arecord' command not found. Please ensure ALSA utils are installed.")
                sys.exit(1)
                
            # The loop continues immediately after the recording finishes
            
    except KeyboardInterrupt:
        print("\nRecording stopped by user.")

if __name__ == "__main__":
    record_audio()
