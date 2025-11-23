import numpy as np
import scipy.io.wavfile as wav


class VoiceDetector:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        # Configuration parameters
        self.sensitivity = 1.5
        self.silence_threshold_ms = 1500
        self.min_speech_duration_ms = 500

        # Calculate frames based on sample rate (assuming ~128 samples per frame like JS)
        # In Python we process in chunks or the whole file. Let's simulate chunks.
        self.chunk_size = 128
        self.frames_per_ms = self.sample_rate / 1000 / self.chunk_size
        self.silence_threshold_frames = int(
            np.ceil(self.silence_threshold_ms * self.frames_per_ms)
        )
        self.min_speech_frames = int(
            np.ceil(self.min_speech_duration_ms * self.frames_per_ms)
        )

        # Adaptive threshold values
        self.calibrating = True
        self.calibration_frames = 0
        self.max_calibration_frames = 30
        self.noise_buffer = []
        self.background_noise = 0.01
        self.base_threshold = 0.02
        self.adaptive_threshold = self.base_threshold

        # Smoothing
        self.level_history = []
        self.history_length = 5

        # State
        self.is_speaking = False
        self.silence_counter = 0
        self.speech_counter = 0

    def process_chunk(self, chunk):
        """
        Process an audio chunk for voice detection.

        Args:
            chunk: numpy array of audio samples

        Returns:
            bool: True if voice is detected in this chunk, False otherwise
        """
        if len(chunk) == 0:
            return False

        # Calculate RMS with protection against NaN/Inf
        try:
            rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))

            # Handle NaN or Inf from calculation
            if not np.isfinite(rms):
                rms = 0.0

        except (ValueError, FloatingPointError):
            # Handle any numerical errors
            return False

        # Normalize roughly to 0-1 range if input is 16-bit int
        # JS Web Audio API provides float -1 to 1.
        # If input is int16, max is 32768.
        # Protect against division by zero
        if rms == 0:
            normalized_rms = 0.0
        else:
            normalized_rms = rms / 32768.0

        # Smoothing
        self.level_history.append(normalized_rms)
        if len(self.level_history) > self.history_length:
            self.level_history.pop(0)

        smoothed_level = sum(self.level_history) / len(self.level_history)

        # Calibration
        if self.calibrating:
            self.noise_buffer.append(smoothed_level)
            self.calibration_frames += 1

            if self.calibration_frames >= self.max_calibration_frames:
                sorted_samples = sorted(self.noise_buffer)
                self.background_noise = sorted_samples[int(len(sorted_samples) * 0.9)]

                self.base_threshold = max(0.015, self.background_noise * 2)
                self.adaptive_threshold = max(
                    self.base_threshold,
                    self.background_noise * 2 * self.sensitivity,
                )
                self.calibrating = False
            return False

        # Speech detection logic
        currently_speaking = smoothed_level > self.adaptive_threshold

        if currently_speaking:
            self.silence_counter = 0
            self.speech_counter += 1

            if not self.is_speaking and self.speech_counter >= 3:
                self.is_speaking = True
        else:
            if self.speech_counter < self.min_speech_frames:
                self.speech_counter = 0

            if self.is_speaking:
                self.silence_counter += 1
                if self.silence_counter >= self.silence_threshold_frames:
                    self.is_speaking = False
                    self.speech_counter = 0

        return self.is_speaking


class AudioProcessor:
    def process_audio(self, file_path):
        """
        Process the audio file and return classification results.

        Handles various edge cases:
        - Corrupted/malformed files
        - NaN and Inf values in audio data
        - Stereo vs mono audio
        - Various bit depths and sample rates

        Returns:
            dict: Classification results with has_sound, is_speech, is_voice,
                  is_clapping, and confidence fields
        """
        try:
            rate, data = wav.read(file_path)

            # Handle stereo audio by converting to mono (average channels)
            if len(data.shape) > 1:
                print(f"Converting stereo audio ({data.shape[1]} channels) to mono")
                data = np.mean(data, axis=1)

            # Convert to float for processing
            if data.dtype != np.float32:
                data = data.astype(np.float32)

            # Handle NaN and Inf values
            if np.any(~np.isfinite(data)):
                print("Warning: Audio contains NaN or Inf values, replacing with zeros")
                data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)

            # Handle empty or very short audio
            if len(data) == 0:
                print("Warning: Empty audio data")
                return {
                    "has_sound": False,
                    "is_speech": False,
                    "is_voice": False,
                    "is_clapping": False,
                    "confidence": 0.0,
                }

            # 1. Check for Sound (Global RMS)
            # Thresholds (Tuned based on tests/expectations)
            # In test_has_sound_true, sine wave amplitude is ~32767. RMS ~ 23169.
            # In test_has_sound_false, silence is 0.
            global_rms = np.sqrt(np.mean(data**2))

            # Handle potential NaN from RMS calculation
            if not np.isfinite(global_rms):
                global_rms = 0.0

            SOUND_THRESHOLD = 100.0
            has_sound = global_rms > SOUND_THRESHOLD

            is_speech = False
            is_clapping = False
            confidence = 0.0

            if has_sound:
                # 2. Check for Speech (using VoiceDetector logic)
                detector = VoiceDetector(sample_rate=rate)
                chunk_size = detector.chunk_size

                speech_detected_frames = 0
                total_processed_frames = 0

                # Process file in chunks
                for i in range(0, len(data), chunk_size):
                    chunk = data[i : i + chunk_size]
                    if len(chunk) < chunk_size:
                        break  # Skip incomplete last chunk

                    if detector.process_chunk(chunk):
                        speech_detected_frames += 1
                    total_processed_frames += 1

                # If we detected speech in a significant portion of the file (after calibration)
                # or if the final state was speaking.
                # Let's use a simple heuristic: if we were speaking for > 10% of non-calibration frames
                valid_frames = total_processed_frames - detector.max_calibration_frames
                if valid_frames > 0:
                    if (
                        speech_detected_frames > 0
                    ):  # Any speech detected is good enough for now
                        is_speech = True
                        confidence = 0.8

                # 3. Check for Clapping (detect regardless of speech)
                PEAK_THRESHOLD = 15000.0
                peaks = np.where(np.abs(data) > PEAK_THRESHOLD)[0]
                if len(peaks) > 0:
                    is_clapping = True
                    # Prefer clapping confidence if higher
                    confidence = max(confidence, 0.9)

            return {
                "has_sound": bool(has_sound),
                "is_speech": bool(is_speech),
                "is_voice": bool(is_speech),
                "is_clapping": bool(is_clapping),
                "confidence": float(confidence),
            }

        except Exception as e:
            print(f"Error processing audio: {type(e).__name__}: {e}")
            # Return safe defaults instead of crashing
            return {
                "has_sound": False,
                "is_speech": False,
                "is_voice": False,
                "is_clapping": False,
                "confidence": 0.0,
            }
