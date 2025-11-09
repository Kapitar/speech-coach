import google.generativeai as genai
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any

from app.config import GOOGLE_AI_STUDIO_API_KEY, GEMINI_MODEL, GENERATION_CONFIG, PROMPTS_DIR

logger = logging.getLogger(__name__)

class SpeechAnalyzer:
    """Analyzes speech videos using Gemini and the general_prompt.txt schema."""
    
    def __init__(self):
        genai.configure(api_key=GOOGLE_AI_STUDIO_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.system_prompt = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Load the general analysis prompt."""
        prompt_path = PROMPTS_DIR / "general_prompt.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")
    
    def _wait_for_file_active(self, file, timeout: int = 120) -> None:
        """
        Wait for uploaded file to become ACTIVE.
        
        Args:
            file: The uploaded file object
            timeout: Maximum seconds to wait (default 120)
            
        Raises:
            TimeoutError: If file doesn't become active within timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            file = genai.get_file(file.name)
            if file.state.name == "ACTIVE":
                logger.info(f"File {file.name} is now ACTIVE")
                return
            elif file.state.name == "FAILED":
                raise RuntimeError(f"File {file.name} processing FAILED")
            
            logger.info(f"File {file.name} state: {file.state.name}, waiting...")
            time.sleep(2)
        
        raise TimeoutError(f"File {file.name} did not become ACTIVE within {timeout} seconds")
    
    async def analyze_video(self, video_path: str, audio_path: str = None) -> Dict[str, Any]:
        """
        Analyze a video file and return structured feedback.
        
        Args:
            video_path: Path to the video file
            audio_path: Optional path to separate audio file
            
        Returns:
            Dictionary matching the feedback schema from general_prompt.txt
        """
        video_file = None
        audio_file = None
        
        try:
            logger.info(f"Starting analysis for video: {video_path}")
            
            # Upload video file
            video_file = genai.upload_file(path=video_path)
            logger.info(f"Uploaded video: {video_file.name}, state: {video_file.state.name}")
            
            # Wait for file to be processed
            self._wait_for_file_active(video_file)
            
            # Prepare content parts
            content_parts = [self.system_prompt, video_file]
            
            # If separate audio provided, upload and include it
            if audio_path:
                audio_file = genai.upload_file(path=audio_path)
                logger.info(f"Uploaded audio: {audio_file.name}, state: {audio_file.state.name}")
                self._wait_for_file_active(audio_file)
                content_parts.append(audio_file)
            
            # Generate analysis
            logger.info("Generating analysis with Gemini...")
            response = self.model.generate_content(
                content_parts,
                generation_config=GENERATION_CONFIG
            )
            
            # Parse JSON response
            raw_text = response.text.strip()
            
            # Remove markdown code fences if present (safety measure)
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()
            
            feedback_json = json.loads(raw_text)
            logger.info("Successfully parsed feedback JSON")
            
            return feedback_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {raw_text[:500]}...")
            raise ValueError(f"Invalid JSON response from model: {e}")
        except TimeoutError as e:
            logger.error(f"File processing timeout: {e}")
            raise RuntimeError(f"Video processing timed out. Please try with a smaller video or try again later.")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
        finally:
            # Clean up uploaded files from Gemini's storage
            try:
                if video_file:
                    genai.delete_file(video_file.name)
                    logger.info(f"Deleted video file: {video_file.name}")
                if audio_file:
                    genai.delete_file(audio_file.name)
                    logger.info(f"Deleted audio file: {audio_file.name}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup files: {cleanup_error}")
