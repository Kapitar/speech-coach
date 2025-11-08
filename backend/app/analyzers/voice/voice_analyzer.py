import librosa
import numpy as np
import soundfile as sf
from scipy import signal
from app.models import VoiceQualityMetrics


class VoiceAnalyzer:
    """Analyzes voice quality including volume, pitch, and clarity"""
    
    def __init__(self):
        self.sample_rate = 22050  # Standard sample rate for analysis
    
    def analyze(self, audio_path: str) -> VoiceQualityMetrics:
        """Analyze voice quality from audio file"""
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            if len(y) == 0:
                raise Exception("Audio file is empty")
            
            # Calculate volume (RMS energy in dB)
            rms = librosa.feature.rms(y=y)[0]
            rms_db = librosa.power_to_db(rms**2, ref=np.max)
            avg_volume = np.mean(rms_db)
            
            # Volume consistency (lower std = more consistent)
            volume_std = np.std(rms_db)
            volume_consistency = 1.0 / (1.0 + volume_std / 10)  # Normalize to 0-1
            
            # Calculate pitch (fundamental frequency)
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                # Filter out unrealistic pitches (human voice is typically 50-500 Hz)
                # This filters out harmonics and noise
                if pitch > 0 and 50 <= pitch <= 500:
                    pitch_values.append(pitch)
            
            if pitch_values:
                avg_pitch = np.mean(pitch_values)
                pitch_range = np.max(pitch_values) - np.min(pitch_values)
            else:
                avg_pitch = 150  # Default
                pitch_range = 50
            
            # Voice stability (pitch variation)
            if len(pitch_values) > 1:
                pitch_std = np.std(pitch_values)
                # Lower variation = more stable
                voice_stability = 1.0 / (1.0 + pitch_std / 20)
            else:
                voice_stability = 0.7
            
            # Clarity score (based on spectral centroid and zero crossing rate)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            
            # Higher spectral centroid and moderate ZCR indicate clarity
            avg_spectral_centroid = np.mean(spectral_centroids)
            avg_zcr = np.mean(zcr)
            
            # Normalize clarity score (0-1)
            clarity_score = min(1.0, (avg_spectral_centroid / 3000) * (1 - min(avg_zcr, 0.1) * 5))
            
            # Generate feedback
            feedback = []
            if volume_consistency < 0.7:
                feedback.append("Your volume varies significantly. Practice maintaining consistent volume.")
            if clarity_score < 0.7:
                feedback.append("Work on enunciating clearly. Practice speaking more deliberately.")
            if voice_stability < 0.6:
                feedback.append("Your pitch varies a lot. Work on maintaining a more stable voice.")
            if avg_volume < -30:
                feedback.append("Your volume is quite low. Speak up to ensure you're heard clearly.")
            
            if not feedback:
                feedback.append("Your voice quality is excellent! Clear, consistent, and well-projected.")
            
            return VoiceQualityMetrics(
                average_volume=float(avg_volume),
                volume_consistency=float(volume_consistency),
                clarity_score=float(clarity_score),
                pitch_range=float(pitch_range),
                average_pitch=float(avg_pitch),
                voice_stability=float(voice_stability),
                feedback=feedback
            )
            
        except Exception as e:
            # Return default metrics if analysis fails
            return VoiceQualityMetrics(
                average_volume=-20.0,
                volume_consistency=0.7,
                clarity_score=0.7,
                pitch_range=50.0,
                average_pitch=150.0,
                voice_stability=0.7,
                feedback=[f"Could not analyze voice quality: {str(e)}"]
            )

