from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import shutil
from pathlib import Path
from typing import Optional
import io

from app.config import UPLOADS_DIR
from app.services.elevenlabs_service import ElevenLabsService
from app.models import (
    TranscriptionResponse,
    ImprovementResponse,
    FullWorkflowResponse
)

router = APIRouter(prefix="/speech", tags=["Speech Improvement"])
logger = logging.getLogger(__name__)

elevenlabs_service = ElevenLabsService()


def normalize_language_code(code: Optional[str]) -> Optional[str]:
    """Convert empty string, whitespace, string 'None', or 'string' to None for auto-detect."""
    if code is None:
        return None
    if isinstance(code, str):
        stripped = code.strip()
        # Handle empty string, the string literal "None", or the placeholder "string"
        if stripped == "" or stripped.lower() == "none" or stripped.lower() == "string":
            return None
        return stripped
    return code


def normalize_optional_string(value: Optional[str]) -> Optional[str]:
    """Convert empty string, whitespace, string 'None', or 'string' to None."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        # Handle empty string, the string literal "None", or the placeholder "string"
        if stripped == "" or stripped.lower() == "none" or stripped.lower() == "string":
            return None
        return stripped
    return value


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    language_code: Optional[str] = Form(default="", description="Language code (e.g., 'eng', 'spa') or leave empty for auto-detect"),
    diarize: bool = Form(default=False, description="Whether to annotate who is speaking"),
    tag_audio_events: bool = Form(default=False, description="Tag audio events like laughter, applause, etc.")
):
    """
    Transcribe an audio file to text using ElevenLabs.
    
    Supports various audio formats (mp3, wav, m4a, etc.)
    Optional parameters for speaker diarization and audio event tagging.
    """
    audio_path = None
    
    try:
        # Save uploaded audio
        audio_path = UPLOADS_DIR / f"audio_{audio.filename}"
        with audio_path.open("wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        logger.info(f"Saved audio to {audio_path}")
        
        # Transcribe with optional parameters
        transcription = await elevenlabs_service.transcribe_audio(
            str(audio_path),
            language_code=normalize_language_code(language_code),
            diarize=diarize,
            tag_audio_events=tag_audio_events
        )
        
        return TranscriptionResponse(
            original_transcription=transcription
        )
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Cleanup
        if audio_path and audio_path.exists():
            audio_path.unlink()


@router.post("/improve", response_model=ImprovementResponse)
async def improve_speech(
    audio: UploadFile = File(..., description="Audio file to transcribe and improve"),
    improvement_focus: Optional[str] = Form(default="", description="Optional focus areas (e.g., 'clarity', 'persuasiveness')"),
    language_code: Optional[str] = Form(default="", description="Language code (e.g., 'eng', 'spa') or leave empty for auto-detect"),
    diarize: bool = Form(default=False, description="Whether to annotate who is speaking"),
    tag_audio_events: bool = Form(default=False, description="Tag audio events like laughter, applause, etc.")
):
    """
    Transcribe an audio file and improve its content using Gemini AI.
    
    Returns the original transcription and improved version with suggestions.
    Optional parameters for better transcription quality.
    """
    audio_path = None
    
    try:
        # Save uploaded audio
        audio_path = UPLOADS_DIR / f"audio_{audio.filename}"
        with audio_path.open("wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        logger.info(f"Saved audio to {audio_path}")
        
        # Transcribe with optional parameters
        transcription = await elevenlabs_service.transcribe_audio(
            str(audio_path),
            language_code=normalize_language_code(language_code),
            diarize=diarize,
            tag_audio_events=tag_audio_events
        )
        
        # Improve content
        improvements = await elevenlabs_service.improve_speech_content(
            transcription,
            normalize_optional_string(improvement_focus)
        )
        
        return ImprovementResponse(
            original_transcription=transcription,
            improved_content=improvements
        )
        
    except Exception as e:
        logger.error(f"Speech improvement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Speech improvement failed: {str(e)}")
    finally:
        # Cleanup
        if audio_path and audio_path.exists():
            audio_path.unlink()


@router.post("/clone-and-improve")
async def clone_voice_and_improve(
    audio: UploadFile = File(..., description="Audio file to clone voice from"),
    improvement_focus: Optional[str] = Form(default="", description="Optional focus areas for improvement (e.g., 'clarity', 'pacing'). Leave empty for general improvement"),
    language_code: Optional[str] = Form(default="", description="Language code (e.g., 'eng', 'spa') or leave empty for auto-detect"),
    diarize: bool = Form(default=False, description="Whether to annotate who is speaking"),
    tag_audio_events: bool = Form(default=False, description="Tag audio events like laughter, applause, etc.")
):
    """
    Complete workflow: Transcribe -> Improve content -> Clone voice -> Generate improved speech.
    
    Returns the improved audio file in the user's own voice.
    """
    audio_path = None
    
    try:
        # Save uploaded audio
        audio_path = UPLOADS_DIR / f"audio_{audio.filename}"
        with audio_path.open("wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        logger.info(f"Saved audio to {audio_path}")
        
        # Run full workflow with optional parameters
        result = await elevenlabs_service.full_speech_improvement_workflow(
            str(audio_path),
            normalize_optional_string(improvement_focus),
            language_code=normalize_language_code(language_code),
            diarize=diarize,
            tag_audio_events=tag_audio_events
        )
        
        # Return audio as streaming response
        audio_stream = io.BytesIO(result["improved_audio_bytes"])
        
        return StreamingResponse(
            audio_stream,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=improved_speech.mp3",
                "X-Audio-Size": str(result["audio_size"]),
                "X-Transcription-Length": str(len(result["original_transcription"]))
            }
        )
        
    except Exception as e:
        logger.error(f"Clone and improve workflow failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")
    finally:
        # Cleanup
        if audio_path and audio_path.exists():
            audio_path.unlink()


@router.post("/clone-and-improve-detailed", response_model=FullWorkflowResponse)
async def clone_voice_and_improve_detailed(
    audio: UploadFile = File(..., description="Audio file to clone voice from"),
    improvement_focus: Optional[str] = Form(default="", description="Optional focus areas for improvement (e.g., 'clarity', 'pacing'). Leave empty for general improvement"),
    language_code: Optional[str] = Form(default="", description="Language code (e.g., 'eng', 'spa') or leave empty for auto-detect"),
    diarize: bool = Form(default=False, description="Whether to annotate who is speaking"),
    tag_audio_events: bool = Form(default=False, description="Tag audio events like laughter, applause, etc.")
):
    """
    Complete workflow with detailed JSON response including transcription, improvements, and metadata.
    The audio file is included as base64 in the response.
    """
    audio_path = None
    
    try:
        # Save uploaded audio
        audio_path = UPLOADS_DIR / f"audio_{audio.filename}"
        with audio_path.open("wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        logger.info(f"Saved audio to {audio_path}")
        
        # Run full workflow with optional parameters
        result = await elevenlabs_service.full_speech_improvement_workflow(
            str(audio_path),
            normalize_optional_string(improvement_focus),
            language_code=normalize_language_code(language_code),
            diarize=diarize,
            tag_audio_events=tag_audio_events
        )
        
        import base64
        audio_base64 = base64.b64encode(result["improved_audio_bytes"]).decode('utf-8')
        
        return JSONResponse(content={
            "original_transcription": result["original_transcription"],
            "improved_content": result["improved_content"],
            "audio_generated": True,
            "audio_size": result["audio_size"],
            "audio_base64": audio_base64
        })
        
    except Exception as e:
        logger.error(f"Clone and improve detailed workflow failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")
    finally:
        # Cleanup
        if audio_path and audio_path.exists():
            audio_path.unlink()


@router.post("/generate-from-video")
async def generate_ideal_speech_from_video(
    video: UploadFile = File(..., description="Video file to extract audio from and improve"),
    improvement_focus: Optional[str] = Form(default="", description="Optional focus areas for improvement (e.g., 'clarity', 'pacing'). Leave empty for general improvement"),
    language_code: Optional[str] = Form(default="", description="Language code (e.g., 'eng', 'spa') or leave empty for auto-detect"),
    diarize: bool = Form(default=False, description="Whether to annotate who is speaking"),
    tag_audio_events: bool = Form(default=False, description="Tag audio events like laughter, applause, etc.")
):
    """
    Accept a VIDEO file, extract audio, then run the complete speech improvement workflow.
    
    Returns JSON with transcription, improved content, and audio as base64.
    This endpoint is designed for frontend compatibility.
    """
    video_path = None
    audio_path = None
    
    try:
        # Save uploaded video
        video_path = UPLOADS_DIR / f"video_{video.filename}"
        with video_path.open("wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        logger.info(f"Saved video to {video_path}")
        
        # Extract audio from video
        audio_path = await elevenlabs_service.extract_audio_from_video(str(video_path))
        logger.info(f"Extracted audio to {audio_path}")
        
        # Run full workflow with optional parameters
        result = await elevenlabs_service.full_speech_improvement_workflow(
            audio_path,
            normalize_optional_string(improvement_focus),
            language_code=normalize_language_code(language_code),
            diarize=diarize,
            tag_audio_events=tag_audio_events
        )
        
        import base64
        audio_base64 = base64.b64encode(result["improved_audio_bytes"]).decode('utf-8')
        
        return JSONResponse(content={
            "original_transcription": result["original_transcription"],
            "improved_content": result["improved_content"],
            "audio_generated": True,
            "audio_size": result["audio_size"],
            "audio_base64": audio_base64
        })
        
    except Exception as e:
        logger.error(f"Generate from video workflow failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")
    finally:
        # Cleanup
        if video_path and video_path.exists():
            video_path.unlink()
        if audio_path and Path(audio_path).exists():
            Path(audio_path).unlink()
