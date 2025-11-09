from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import logging
import shutil
from pathlib import Path

from app.config import UPLOADS_DIR
from app.services.analyzer import SpeechAnalyzer
from app.models import FeedbackResponse

router = APIRouter(prefix="/analyze", tags=["Analysis"])
logger = logging.getLogger(__name__)

analyzer = SpeechAnalyzer()

@router.post("/video", response_model=FeedbackResponse)
async def analyze_video(
    video: UploadFile = File(..., description="Video file to analyze")
):
    """
    Analyze a speech video and return structured feedback following the general_prompt.txt schema.
    
    Returns feedback with:
    - non_verbal: eye_contact, gestures, posture
    - delivery: clarity_enunciation, intonation, eloquence_filler_words
    - content: organization_flow, persuasiveness_impact, clarity_of_message
    - overall_feedback: summary, strengths, areas_to_improve, prioritized_actions
    """
    video_path = None
    
    try:
        # Save uploaded video
        video_path = UPLOADS_DIR / f"video_{video.filename}"
        with video_path.open("wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        logger.info(f"Saved video to {video_path}")
        
        # Analyze
        feedback = await analyzer.analyze_video(
            str(video_path),
            None
        )
        
        return JSONResponse(content=feedback)
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Cleanup
        if video_path and video_path.exists():
            video_path.unlink()
