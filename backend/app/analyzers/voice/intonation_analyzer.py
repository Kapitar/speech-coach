import librosa
import numpy as np
from scipy import signal
from app.models import IntonationMetrics


class IntonationAnalyzer:
    """Analyzes intonation, prosody, and pitch variation"""
    
    def __init__(self):
        self.sample_rate = 22050
    
    def analyze(self, audio_path: str) -> IntonationMetrics:
        """Analyze intonation and prosody from audio"""
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            if len(y) == 0:
                raise Exception("Audio file is empty")
            
            # Extract pitch (fundamental frequency)
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if not pitch_values:
                # Fallback: use default values
                return IntonationMetrics(
                    pitch_variation=0.3,
                    stress_pattern_score=0.5,
                    monotone_score=0.7,
                    energy_variation=0.4,
                    prosody_score=0.5,
                    feedback=["Could not extract pitch information from audio."]
                )
            
            pitch_values = np.array(pitch_values)
            
            # Calculate pitch variation (coefficient of variation)
            if np.mean(pitch_values) > 0:
                pitch_cv = np.std(pitch_values) / np.mean(pitch_values)
                pitch_variation = min(1.0, pitch_cv * 2)  # Normalize to 0-1
            else:
                pitch_variation = 0.3
            
            # Calculate monotone score (inverse of variation)
            # Higher score = more monotone (bad)
            monotone_score = 1.0 - pitch_variation
            
            # Calculate energy variation (RMS energy variation)
            rms = librosa.feature.rms(y=y)[0]
            if len(rms) > 1:
                energy_cv = np.std(rms) / (np.mean(rms) + 1e-10)
                energy_variation = min(1.0, energy_cv * 3)
            else:
                energy_variation = 0.4
            
            # Stress pattern score (based on energy peaks and pitch changes)
            # Look for rhythmic patterns in energy
            rms_smooth = signal.savgol_filter(rms, min(51, len(rms) // 2 * 2 + 1), 3) if len(rms) > 50 else rms
            peaks, _ = signal.find_peaks(rms_smooth, height=np.mean(rms_smooth))
            
            # More peaks indicate better stress patterns
            if len(rms) > 0:
                peak_density = len(peaks) / len(rms)
                stress_pattern_score = min(1.0, peak_density * 10)
            else:
                stress_pattern_score = 0.5
            
            # Overall prosody score (combination of factors)
            prosody_score = (
                pitch_variation * 0.4 +
                energy_variation * 0.3 +
                stress_pattern_score * 0.3
            )
            
            # Generate feedback
            feedback = []
            if monotone_score > 0.6:
                feedback.append("Your speech is somewhat monotone. Vary your pitch to add interest and emphasis.")
            if pitch_variation < 0.3:
                feedback.append("Your pitch variation is limited. Practice using different pitch levels for emphasis.")
            if energy_variation < 0.3:
                feedback.append("Your energy level is too constant. Vary your volume and intensity for better engagement.")
            if stress_pattern_score < 0.5:
                feedback.append("Work on creating clearer stress patterns. Emphasize key words and phrases.")
            if prosody_score < 0.5:
                feedback.append("Your overall prosody needs improvement. Practice varying pitch, volume, and rhythm.")
            
            if not feedback:
                feedback.append("Excellent intonation! Your speech has good variation and prosody.")
            
            return IntonationMetrics(
                pitch_variation=float(pitch_variation),
                stress_pattern_score=float(stress_pattern_score),
                monotone_score=float(monotone_score),
                energy_variation=float(energy_variation),
                prosody_score=float(prosody_score),
                feedback=feedback
            )
            
        except Exception as e:
            # Return default metrics if analysis fails
            return IntonationMetrics(
                pitch_variation=0.3,
                stress_pattern_score=0.5,
                monotone_score=0.7,
                energy_variation=0.4,
                prosody_score=0.5,
                feedback=[f"Could not analyze intonation: {str(e)}"]
            )

