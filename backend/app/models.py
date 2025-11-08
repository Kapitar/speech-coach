from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum


class PostureMetrics(BaseModel):
    """Metrics related to body posture"""
    average_shoulder_alignment: float  # 0-1, higher is better
    average_back_straightness: float  # 0-1, higher is better
    stability_score: float  # 0-1, measures how still the speaker is
    confidence_score: float  # 0-1, based on posture openness
    feedback: List[str]


class EyeContactMetrics(BaseModel):
    """Metrics related to eye contact"""
    eye_contact_percentage: float  # 0-100, percentage of time looking at camera
    average_eye_contact_duration: float  # seconds
    gaze_shifts_per_minute: float
    direct_eye_contact_score: float  # 0-1
    feedback: List[str]


class VoiceQualityMetrics(BaseModel):
    """Metrics related to voice quality"""
    average_volume: float  # dB
    volume_consistency: float  # 0-1, higher is more consistent
    clarity_score: float  # 0-1, based on audio quality
    pitch_range: float  # Hz range
    average_pitch: float  # Hz
    voice_stability: float  # 0-1
    feedback: List[str]


class SpeechDisfluencyMetrics(BaseModel):
    """Metrics related to speech disfluencies"""
    stutter_count: int
    filler_word_count: int  # "um", "uh", "like", etc.
    pause_count: int
    total_disfluencies: int
    disfluency_rate: float  # per minute
    speech_rate: float  # words per minute
    feedback: List[str]


class IntonationMetrics(BaseModel):
    """Metrics related to intonation and prosody"""
    pitch_variation: float  # 0-1, higher is more varied
    stress_pattern_score: float  # 0-1
    monotone_score: float  # 0-1, higher means more monotone (bad)
    energy_variation: float  # 0-1
    prosody_score: float  # 0-1, overall prosody quality
    feedback: List[str]


# CV-specific models
class CVMetrics(BaseModel):
    """Combined computer vision metrics"""
    posture: PostureMetrics
    eye_contact: EyeContactMetrics
    
    def calculate_cv_score(self) -> float:
        """Calculate CV-specific score from 0-100"""
        posture_score = (
            self.posture.average_shoulder_alignment * 0.3 +
            self.posture.average_back_straightness * 0.3 +
            self.posture.stability_score * 0.2 +
            self.posture.confidence_score * 0.2
        ) * 100
        
        eye_contact_score = (
            self.eye_contact.eye_contact_percentage / 100 * 0.6 +
            self.eye_contact.direct_eye_contact_score * 0.4
        ) * 100
        
        # Weighted average: 40% posture, 60% eye contact
        cv_score = posture_score * 0.4 + eye_contact_score * 0.6
        return round(cv_score, 2)
    
    def generate_cv_feedback(self) -> List[str]:
        """Generate CV-specific feedback"""
        feedback = []
        
        if self.posture.average_shoulder_alignment < 0.7:
            feedback.append("Try to keep your shoulders aligned and level. This projects confidence.")
        if self.posture.stability_score < 0.6:
            feedback.append("Work on maintaining a stable, grounded posture. Avoid excessive swaying.")
        if self.eye_contact.eye_contact_percentage < 60:
            feedback.append(f"Your eye contact is at {self.eye_contact.eye_contact_percentage:.1f}%. Aim for 70-80% for better engagement.")
        if self.eye_contact.gaze_shifts_per_minute > 20:
            feedback.append("Your gaze shifts frequently. Try to maintain eye contact for 3-5 seconds before shifting.")
        
        if not feedback:
            feedback.append("Great visual presence! Your posture and eye contact are excellent.")
        
        return feedback


class VoiceMetrics(BaseModel):
    """Combined voice analysis metrics"""
    voice_quality: VoiceQualityMetrics
    speech_disfluencies: SpeechDisfluencyMetrics
    intonation: IntonationMetrics
    
    def calculate_voice_score(self) -> float:
        """Calculate voice-specific score from 0-100"""
        voice_score = (
            self.voice_quality.clarity_score * 0.3 +
            self.voice_quality.volume_consistency * 0.3 +
            self.voice_quality.voice_stability * 0.4
        ) * 100
        
        # Lower disfluency rate is better
        disfluency_score = max(0, 100 - (self.speech_disfluencies.disfluency_rate * 10))
        
        intonation_score = (
            (1 - self.intonation.monotone_score) * 0.4 +
            self.intonation.prosody_score * 0.6
        ) * 100
        
        # Weighted average: 35% voice quality, 35% disfluencies, 30% intonation
        voice_overall = voice_score * 0.35 + disfluency_score * 0.35 + intonation_score * 0.30
        return round(voice_overall, 2)
    
    def generate_voice_feedback(self) -> List[str]:
        """Generate voice-specific feedback"""
        feedback = []
        
        if self.voice_quality.volume_consistency < 0.7:
            feedback.append("Your volume varies significantly. Practice maintaining consistent volume throughout your speech.")
        if self.voice_quality.clarity_score < 0.7:
            feedback.append("Work on enunciating clearly. Practice speaking more deliberately.")
        if self.speech_disfluencies.disfluency_rate > 5:
            feedback.append(f"You have {self.speech_disfluencies.disfluency_rate:.1f} disfluencies per minute. Practice pausing instead of using filler words.")
        if self.speech_disfluencies.filler_word_count > 10:
            feedback.append(f"You used {self.speech_disfluencies.filler_word_count} filler words. Try replacing them with brief pauses.")
        if self.intonation.monotone_score > 0.6:
            feedback.append("Your speech is somewhat monotone. Vary your pitch and energy to keep the audience engaged.")
        if self.intonation.prosody_score < 0.6:
            feedback.append("Work on varying your intonation and stress patterns to add emphasis and interest.")
        
        if not feedback:
            feedback.append("Excellent voice quality! Your speech is clear, engaging, and well-paced.")
        
        return feedback


# Combined models (for full analysis)
class AnalysisMetrics(BaseModel):
    """Combined metrics from all analyses"""
    posture: PostureMetrics
    eye_contact: EyeContactMetrics
    voice_quality: VoiceQualityMetrics
    speech_disfluencies: SpeechDisfluencyMetrics
    intonation: IntonationMetrics
    
    def calculate_overall_score(self) -> float:
        """Calculate overall score from 0-100"""
        weights = {
            'posture': 0.15,
            'eye_contact': 0.20,
            'voice_quality': 0.20,
            'speech_disfluencies': 0.20,
            'intonation': 0.25
        }
        
        posture_score = (
            self.posture.average_shoulder_alignment * 0.3 +
            self.posture.average_back_straightness * 0.3 +
            self.posture.stability_score * 0.2 +
            self.posture.confidence_score * 0.2
        ) * 100
        
        eye_contact_score = (
            self.eye_contact.eye_contact_percentage / 100 * 0.6 +
            self.eye_contact.direct_eye_contact_score * 0.4
        ) * 100
        
        voice_score = (
            self.voice_quality.clarity_score * 0.3 +
            self.voice_quality.volume_consistency * 0.3 +
            self.voice_quality.voice_stability * 0.4
        ) * 100
        
        # Lower disfluency rate is better
        disfluency_score = max(0, 100 - (self.speech_disfluencies.disfluency_rate * 10))
        
        intonation_score = (
            (1 - self.intonation.monotone_score) * 0.4 +
            self.intonation.prosody_score * 0.6
        ) * 100
        
        overall = (
            posture_score * weights['posture'] +
            eye_contact_score * weights['eye_contact'] +
            voice_score * weights['voice_quality'] +
            disfluency_score * weights['speech_disfluencies'] +
            intonation_score * weights['intonation']
        )
        
        return round(overall, 2)
    
    def generate_feedback(self) -> List[str]:
        """Generate actionable feedback based on metrics"""
        feedback = []
        
        # Posture feedback
        if self.posture.average_shoulder_alignment < 0.7:
            feedback.append("Try to keep your shoulders aligned and level. This projects confidence.")
        if self.posture.stability_score < 0.6:
            feedback.append("Work on maintaining a stable, grounded posture. Avoid excessive swaying.")
        
        # Eye contact feedback
        if self.eye_contact.eye_contact_percentage < 60:
            feedback.append(f"Your eye contact is at {self.eye_contact.eye_contact_percentage:.1f}%. Aim for 70-80% for better engagement.")
        if self.eye_contact.gaze_shifts_per_minute > 20:
            feedback.append("Your gaze shifts frequently. Try to maintain eye contact for 3-5 seconds before shifting.")
        
        # Voice quality feedback
        if self.voice_quality.volume_consistency < 0.7:
            feedback.append("Your volume varies significantly. Practice maintaining consistent volume throughout your speech.")
        if self.voice_quality.clarity_score < 0.7:
            feedback.append("Work on enunciating clearly. Practice speaking more deliberately.")
        
        # Disfluency feedback
        if self.speech_disfluencies.disfluency_rate > 5:
            feedback.append(f"You have {self.speech_disfluencies.disfluency_rate:.1f} disfluencies per minute. Practice pausing instead of using filler words.")
        if self.speech_disfluencies.filler_word_count > 10:
            feedback.append(f"You used {self.speech_disfluencies.filler_word_count} filler words. Try replacing them with brief pauses.")
        
        # Intonation feedback
        if self.intonation.monotone_score > 0.6:
            feedback.append("Your speech is somewhat monotone. Vary your pitch and energy to keep the audience engaged.")
        if self.intonation.prosody_score < 0.6:
            feedback.append("Work on varying your intonation and stress patterns to add emphasis and interest.")
        
        if not feedback:
            feedback.append("Great job! Your speech demonstrates strong fundamentals across all metrics.")
        
        return feedback


# Response models
class CVResponse(BaseModel):
    """Response model for CV analysis endpoint"""
    success: bool
    metrics: CVMetrics
    score: float
    feedback: List[str]


class VoiceResponse(BaseModel):
    """Response model for voice analysis endpoint"""
    success: bool
    metrics: VoiceMetrics
    score: float
    feedback: List[str]


class AnalysisResponse(BaseModel):
    """Response model for combined analysis endpoint"""
    success: bool
    metrics: AnalysisMetrics
    overall_score: float
    feedback: List[str]

