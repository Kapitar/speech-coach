from fastapi import APIRouter, UploadFile, File, HTTPException
import tempfile
import os
from pathlib import Path

from app.models import CVResponse, CVMetrics
from app.video_processor import VideoProcessor
from app.analyzers.cv.posture_analyzer import PostureAnalyzer
from app.analyzers.cv.eye_contact_analyzer import EyeContactAnalyzer

router = APIRouter(prefix="/cv", tags=["cv"])

# Initialize analyzers
posture_analyzer = PostureAnalyzer()
eye_contact_analyzer = EyeContactAnalyzer()


@router.post("/analyze", response_model=CVResponse)
async def analyze_cv(video: UploadFile = File(...)):
    """
    Analyze computer vision metrics from video:
    - Posture (shoulder alignment, back straightness, stability)
    - Eye contact (gaze direction, contact percentage, shifts)
    """
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Save uploaded video to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video.filename).suffix) as tmp_file:
        try:
            # Write video content
            content = await video.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
            
            # Run CV analyses
            posture_metrics = posture_analyzer.analyze(tmp_file_path)
            eye_contact_metrics = eye_contact_analyzer.analyze(tmp_file_path)
            
            # Combine metrics
            combined_metrics = CVMetrics(
                posture=posture_metrics,
                eye_contact=eye_contact_metrics
            )
            
            # Calculate score and feedback
            score = combined_metrics.calculate_cv_score()
            feedback = combined_metrics.generate_cv_feedback()
            
            return CVResponse(
                success=True,
                metrics=combined_metrics,
                score=score,
                feedback=feedback
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"CV analysis failed: {str(e)}")
        finally:
            # Cleanup temporary files
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

