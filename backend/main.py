from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import tempfile
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path to import gesture_analyzer
sys.path.append(str(Path(__file__).parent.parent))

from gesture_analyzer import GestureAnalyzer

app = FastAPI(title="Speech Coach API", version="1.0.0")

# Initialize the gesture analyzer (will raise error if API key not set)
try:
    analyzer = GestureAnalyzer()
except ValueError as e:
    print(f"Warning: GestureAnalyzer initialization failed: {e}")
    analyzer = None


@app.get("/")
async def root():
    return {"message": "Hello World", "endpoints": {
        "analyze_gestures": "POST /analyze-gestures - Upload a video file for gesture analysis"
    }}


@app.post("/analyze-gestures")
async def analyze_gestures(
    file: UploadFile = File(...),
):
    """
    Analyze gestures and body posture in an uploaded video file.
    
    Args:
        file: Video file to analyze (MP4, AVI, MOV, etc.)
    
    Returns:
        JSON response with analysis results including:
        - overall_summary: Overall analysis summary
        - time_periods: Analysis for each video segment
        - metrics: Calculated metrics (frequency, variety, consistency, engagement)
        - recommendations: Improvement recommendations
    """
    # Check if analyzer is initialized
    if analyzer is None:
        raise HTTPException(
            status_code=500,
            detail="Gesture analyzer is not initialized. Please check GOOGLE_AI_STUDIO_API_KEY environment variable."
        )
    
    # Validate file type
    allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
    file_extension = Path(file.filename).suffix.lower() if file.filename else ''
    
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File filename is required"
        )
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_extension}. "
                   f"Supported formats: {', '.join(allowed_extensions)}"
        )
    
    # Validate API key
    if not os.getenv("GOOGLE_AI_STUDIO_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_AI_STUDIO_API_KEY environment variable is not set"
        )
    
    # Create temporary file for uploaded video
    temp_file = None
    temp_file_path = None
    
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Validate file size (e.g., max 500MB)
        file_size = os.path.getsize(temp_file_path)
        max_size = 500 * 1024 * 1024  # 500MB
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed size (500 MB)"
            )
        
        # Analyze gestures
        try:
            analysis_result = analyzer.analyze_gestures(
                video_path=temp_file_path
            )
        except ValueError as e:
            # Validation errors (invalid file, missing API key, etc.)
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            # Runtime errors (API failures, processing errors, etc.)
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {str(e)}"
            )
        except Exception as e:
            # Unexpected errors
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during video analysis: {str(e)}"
            )
        
        return JSONResponse(content=analysis_result)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                # Log error but don't fail the request
                print(f"Warning: Could not delete temporary file {temp_file_path}: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "gemini_api_configured": bool(os.getenv("GOOGLE_AI_STUDIO_API_KEY"))
    }
