import librosa
import numpy as np
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
import tempfile
import os
from app.models import SpeechDisfluencyMetrics


class SpeechAnalyzer:
    """Analyzes speech for disfluencies, stutters, and filler words"""
    
    def __init__(self):
        self.filler_words = ['um', 'uh', 'er', 'ah', 'like', 'you know', 'so', 'well', 'actually', 'basically']
        self.recognizer = sr.Recognizer()
    
    def detect_pauses(self, audio_path: str, min_silence_len: int = 500, silence_thresh: int = -40) -> int:
        """Detect pauses in speech"""
        try:
            audio = AudioSegment.from_wav(audio_path)
            chunks = split_on_silence(
                audio,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh
            )
            # Number of pauses = number of chunks - 1 (or more if there are silent gaps)
            return max(0, len(chunks) - 1)
        except:
            return 0
    
    def detect_filler_words(self, text: str) -> int:
        """Count filler words in transcribed text"""
        text_lower = text.lower()
        count = 0
        for filler in self.filler_words:
            count += text_lower.count(filler)
        return count
    
    def detect_stutters(self, text: str) -> int:
        """Detect stutters (repeated words or syllables)"""
        words = text.lower().split()
        stutter_count = 0
        i = 0
        while i < len(words) - 1:
            # Check for repeated words (common stutter pattern)
            if words[i] == words[i + 1] and len(words[i]) > 2:
                stutter_count += 1
                i += 2
            # Check for partial word repetitions (e.g., "th-th-the")
            elif i < len(words) - 2 and words[i] == words[i + 2] and len(words[i]) <= 3:
                stutter_count += 1
                i += 3
            else:
                i += 1
        return stutter_count
    
    def calculate_speech_rate(self, text: str, duration_seconds: float) -> float:
        """Calculate words per minute"""
        word_count = len(text.split())
        if duration_seconds > 0:
            return (word_count / duration_seconds) * 60
        return 0
    
    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio to text"""
        try:
            # Check if audio file exists and has content
            file_size = os.path.getsize(audio_path)
            if file_size < 1000:  # Less than 1KB is suspicious
                print(f"Warning: Audio file is very small ({file_size} bytes)")
            
            with sr.AudioFile(audio_path) as source:
                # Adjust for ambient noise to improve recognition
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.record(source)
                
                # Try transcription
                text = self.recognizer.recognize_google(audio)
                if text:
                    print(f"Transcription successful: {text[:100] if len(text) > 100 else text}")
                return text
        except sr.UnknownValueError:
            print("Warning: Speech recognition could not understand audio")
            print("This might mean audio is too quiet, unclear, or contains no speech")
            return ""
        except sr.RequestError as e:
            print(f"Warning: Speech recognition service error: {e}")
            print("Check your internet connection (Google Speech Recognition requires internet)")
            return ""
        except Exception as e:
            print(f"Error during transcription: {e}")
            return ""
    
    def analyze(self, audio_path: str) -> SpeechDisfluencyMetrics:
        """Analyze speech for disfluencies"""
        try:
            # Get audio duration
            y, sr = librosa.load(audio_path, sr=None)
            duration_seconds = len(y) / sr if sr > 0 else 1
            duration_minutes = duration_seconds / 60
            
            # Transcribe audio
            text = self.transcribe_audio(audio_path)
            
            # Detect disfluencies
            filler_count = self.detect_filler_words(text) if text else 0
            stutter_count = self.detect_stutters(text) if text else 0
            pause_count = self.detect_pauses(audio_path)
            
            total_disfluencies = filler_count + stutter_count
            disfluency_rate = total_disfluencies / duration_minutes if duration_minutes > 0 else 0
            
            # Calculate speech rate
            speech_rate = self.calculate_speech_rate(text, duration_seconds) if text else 0
            
            # Generate feedback
            feedback = []
            if stutter_count > 0:
                feedback.append(f"You had {stutter_count} stutter(s). Practice speaking more slowly and deliberately.")
            if filler_count > 10:
                feedback.append(f"You used {filler_count} filler words. Replace them with brief pauses.")
            elif filler_count > 5:
                feedback.append(f"You used {filler_count} filler words. Try to reduce this number.")
            if disfluency_rate > 5:
                feedback.append(f"Your disfluency rate is {disfluency_rate:.1f} per minute. Practice pausing instead of using filler words.")
            if speech_rate > 180:
                feedback.append(f"You're speaking at {speech_rate:.0f} words per minute, which is quite fast. Slow down for better clarity.")
            elif speech_rate < 120 and speech_rate > 0:
                feedback.append(f"You're speaking at {speech_rate:.0f} words per minute, which is slow. Try to maintain a moderate pace.")
            
            if not feedback:
                feedback.append("Great speech! Minimal disfluencies and good pacing.")
            
            return SpeechDisfluencyMetrics(
                stutter_count=stutter_count,
                filler_word_count=filler_count,
                pause_count=pause_count,
                total_disfluencies=total_disfluencies,
                disfluency_rate=float(disfluency_rate),
                speech_rate=float(speech_rate),
                feedback=feedback
            )
            
        except Exception as e:
            # Return default metrics if analysis fails
            return SpeechDisfluencyMetrics(
                stutter_count=0,
                filler_word_count=0,
                pause_count=0,
                total_disfluencies=0,
                disfluency_rate=0.0,
                speech_rate=0.0,
                feedback=[f"Could not analyze speech: {str(e)}"]
            )

