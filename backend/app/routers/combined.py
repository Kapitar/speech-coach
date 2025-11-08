from fastapi import APIRouter, UploadFile, File, HTTPException
import tempfile
import os
from pathlib import Path

from app.models import AnalysisResponse, AnalysisMetrics
from app.video_processor import VideoProcessor
from app.analyzers.cv.posture_analyzer import PostureAnalyzer
from app.analyzers.cv.eye_contact_analyzer import EyeContactAnalyzer
from app.analyzers.voice.voice_analyzer import VoiceAnalyzer
from app.analyzers.voice.speech_analyzer import SpeechAnalyzer
from app.analyzers.voice.intonation_analyzer import IntonationAnalyzer

router = APIRouter(prefix="/analyze", tags=["combined"])

# Initialize analyzers
posture_analyzer = PostureAnalyzer()
eye_contact_analyzer = EyeContactAnalyzer()
voice_analyzer = VoiceAnalyzer()
speech_analyzer = SpeechAnalyzer()
intonation_analyzer = IntonationAnalyzer()


@router.post("", response_model=AnalysisResponse)
async def analyze_full(video: UploadFile = File(...)):
    """
    Analyze all metrics from video (both CV and voice):
    - Posture
    - Eye contact
    - Voice quality
    - Speech disfluencies
    - Intonation
    """
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Save uploaded video to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video.filename).suffix) as tmp_file:
        audio_path = None
        try:
            # Write video content
            content = await video.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
            
            # Process video
            processor = VideoProcessor(tmp_file_path)
            video_path, audio_path = processor.extract_audio()
            
            # Run all analyses
            posture_metrics = posture_analyzer.analyze(video_path)
            eye_contact_metrics = eye_contact_analyzer.analyze(video_path)
            voice_metrics = voice_analyzer.analyze(audio_path)
            speech_metrics = speech_analyzer.analyze(audio_path)
            intonation_metrics = intonation_analyzer.analyze(audio_path)
            
            # Combine all metrics
            combined_metrics = AnalysisMetrics(
                posture=posture_metrics,
                eye_contact=eye_contact_metrics,
                voice_quality=voice_metrics,
                speech_disfluencies=speech_metrics,
                intonation=intonation_metrics
            )
            
            # Calculate overall score and feedback
            overall_score = combined_metrics.calculate_overall_score()
            feedback = combined_metrics.generate_feedback()
            
            return AnalysisResponse(
                success=True,
                metrics=combined_metrics,
                overall_score=overall_score,
                feedback=feedback
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        finally:
            # Cleanup temporary files
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)

