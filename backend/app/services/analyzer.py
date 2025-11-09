import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import json
import logging
import time
import re
from pathlib import Path
from typing import Dict, Any

from app.config import GOOGLE_AI_STUDIO_API_KEY, GEMINI_MODEL, GENERATION_CONFIG, PROMPTS_DIR

logger = logging.getLogger(__name__)

class SpeechAnalyzer:
    """Analyzes speech videos using Gemini and the general_prompt.txt schema."""
    
    def __init__(self):
        genai.configure(api_key=GOOGLE_AI_STUDIO_API_KEY)
        
        # Configure safety settings to allow video analysis
        # For speech coaching, we disable safety filters since videos are educational content
        # BLOCK_NONE = 0, BLOCK_ONLY_HIGH = 1, BLOCK_MEDIUM_AND_ABOVE = 2, BLOCK_LOW_AND_ABOVE = 3
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        self.model = genai.GenerativeModel(
            GEMINI_MODEL,
            safety_settings=self.safety_settings
        )
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
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from text response, handling various formats.
        
        Args:
            text: Raw text response from the model
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            ValueError: If no valid JSON can be extracted
        """
        if not text or not text.strip():
            raise ValueError("Empty response text")
        
        # Strategy 1: Try to find JSON in markdown code blocks
        # Find content between ``` and ``` (handles ```json and ```)
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            json_candidate = match.group(1).strip()
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError as e:
                logger.debug(f"Strategy 1 failed: {e}")
        
        # Strategy 2: Find the first { and last } and try to parse
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_candidate = text[first_brace:last_brace + 1]
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError as e:
                logger.debug(f"Strategy 2 failed: {e}")
        
        # Strategy 3: Try to fix common JSON issues and parse
        # Remove trailing commas before closing braces/brackets
        fixed_text = re.sub(r',(\s*[}\]])', r'\1', text)
        first_brace = fixed_text.find('{')
        last_brace = fixed_text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_candidate = fixed_text[first_brace:last_brace + 1]
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError as e:
                logger.debug(f"Strategy 3 failed: {e}")
                # Log the error position for debugging
                if hasattr(e, 'pos'):
                    logger.debug(f"JSON parse error at position {e.pos}: {e.msg}")
                    logger.debug(f"Context around error: {json_candidate[max(0, e.pos-50):min(len(json_candidate), e.pos+50)]}")
        
        # Strategy 4: Try to find JSON object using balanced braces
        # This handles cases where there might be nested objects
        brace_count = 0
        start_idx = -1
        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    json_candidate = text[start_idx:i+1]
                    try:
                        return json.loads(json_candidate)
                    except json.JSONDecodeError as e:
                        logger.debug(f"Strategy 4 failed: {e}")
                    break
        
        # Strategy 5: Try parsing the entire text as-is
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.debug(f"Strategy 5 failed: {e}")
        
        # If all strategies fail, log the problematic text and raise error
        logger.error(f"Failed to extract JSON from response. First 1000 chars: {text[:1000]}")
        logger.error(f"Last 500 chars: {text[-500:]}")
        raise ValueError("Could not extract valid JSON from model response")
    
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
                generation_config=GENERATION_CONFIG,
                safety_settings=self.safety_settings
            )
            
            # Parse JSON response - handle different response formats
            raw_text = None
            
            # Check for blocked/safety filter responses
            if hasattr(response, 'prompt_feedback'):
                prompt_feedback = response.prompt_feedback
                if hasattr(prompt_feedback, 'block_reason') and prompt_feedback.block_reason:
                    reason = prompt_feedback.block_reason
                    reason_name = reason.name if hasattr(reason, 'name') else str(reason)
                    # Log safety ratings if available
                    if hasattr(prompt_feedback, 'safety_ratings'):
                        logger.error(f"Safety ratings: {prompt_feedback.safety_ratings}")
                    raise ValueError(f"Content was blocked by safety filters: {reason_name} (code: {reason})")
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                # Check for finish reason (safety, recitation, etc.)
                # finish_reason values: 1=STOP (normal), 2=MAX_TOKENS, 3=SAFETY, 4=RECITATION, 5=OTHER
                if hasattr(candidate, 'finish_reason'):
                    finish_reason = candidate.finish_reason
                    # Only raise error if it's a safety-related block (3) or other non-normal reason
                    # 1 = STOP (normal completion), so we allow that
                    if finish_reason and finish_reason != 1:
                        finish_reason_name = finish_reason.name if hasattr(finish_reason, 'name') else str(finish_reason)
                        # Don't raise error for MAX_TOKENS (2) as it might still have valid content
                        if finish_reason == 3:  # SAFETY
                            raise ValueError(f"Response blocked by safety filters: {finish_reason_name}")
                        elif finish_reason not in [1, 2]:  # Not STOP or MAX_TOKENS
                            logger.warning(f"Response finished with reason: {finish_reason_name}, but continuing...")
                
                # Extract text from candidate
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text]
                    if text_parts:
                        raw_text = ' '.join(text_parts).strip()
            
            # Fallback to direct text attribute
            if not raw_text and hasattr(response, 'text') and response.text:
                raw_text = response.text.strip()
            
            if not raw_text:
                # Log response structure for debugging
                logger.error(f"Response structure: {type(response)}")
                logger.error(f"Response attributes: {dir(response)}")
                if hasattr(response, 'candidates'):
                    logger.error(f"Candidates: {response.candidates}")
                raise ValueError("Model response is empty or missing text")
            
            logger.debug(f"Raw response length: {len(raw_text)} characters")
            
            # Extract JSON using robust extraction method
            feedback_json = self._extract_json(raw_text)
            logger.info("Successfully parsed feedback JSON")
            
            return feedback_json
            
        except ValueError as e:
            logger.error(f"Failed to extract JSON from response: {e}")
            if 'raw_text' in locals() and raw_text:
                logger.error(f"Raw response (first 2000 chars): {raw_text[:2000]}")
                logger.error(f"Raw response (last 500 chars): {raw_text[-500:]}")
                # Include response snippet in error message for debugging
                error_msg = f"Invalid JSON response from model: {e}"
                if len(raw_text) > 0:
                    error_msg += f"\nResponse preview (first 500 chars): {raw_text[:500]}"
                raise ValueError(error_msg)
            else:
                raise ValueError(f"Invalid JSON response from model: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            if 'raw_text' in locals() and raw_text:
                logger.error(f"Raw response (first 2000 chars): {raw_text[:2000]}")
                logger.error(f"Raw response (last 500 chars): {raw_text[-500:]}")
                error_msg = f"Invalid JSON response from model: {e}"
                if len(raw_text) > 0:
                    error_msg += f"\nResponse preview (first 500 chars): {raw_text[:500]}"
                raise ValueError(error_msg)
            else:
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
