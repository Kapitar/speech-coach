from fastapi import APIRouter, UploadFile, File, HTTPException
import tempfile
import os
from pathlib import Path

from app.models import VoiceResponse, VoiceMetrics
from app.video_processor import VideoProcessor
from app.analyzers.voice.voice_analyzer import VoiceAnalyzer
from app.analyzers.voice.speech_analyzer import SpeechAnalyzer
from app.analyzers.voice.intonation_analyzer import IntonationAnalyzer

router = APIRouter(prefix="/voice", tags=["voice"])

# Initialize analyzers
voice_analyzer = VoiceAnalyzer()
speech_analyzer = SpeechAnalyzer()
intonation_analyzer = IntonationAnalyzer()


@router.post("/analyze", response_model=VoiceResponse)
async def analyze_voice(video: UploadFile = File(...)):
    """
    Analyze voice-related metrics from video:
    - Voice quality (volume, clarity, pitch)
    - Speech disfluencies (stutters, filler words)
    - Intonation and prosody
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
            
            # Extract audio from video
            processor = VideoProcessor(tmp_file_path)
            _, audio_path = processor.extract_audio()
            
            # Run voice analyses
            voice_metrics = voice_analyzer.analyze(audio_path)
            speech_metrics = speech_analyzer.analyze(audio_path)
            intonation_metrics = intonation_analyzer.analyze(audio_path)
            
            # Combine metrics
            combined_metrics = VoiceMetrics(
                voice_quality=voice_metrics,
                speech_disfluencies=speech_metrics,
                intonation=intonation_metrics
            )
            
            # Calculate score and feedback
            score = combined_metrics.calculate_voice_score()
            feedback = combined_metrics.generate_voice_feedback()
            
            return VoiceResponse(
                success=True,
                metrics=combined_metrics,
                score=score,
                feedback=feedback
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Voice analysis failed: {str(e)}")
        finally:
            # Cleanup temporary files
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)

