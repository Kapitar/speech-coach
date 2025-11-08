"""Gemini API client for gesture and posture analysis."""

import os
import json
from typing import Dict, Any, List

import google.generativeai as genai
import cv2
from PIL import Image


class GeminiAnalysisClient:
    """Client for interacting with Gemini API for video analysis."""
    
    def __init__(self, model_name: str = "gemini-2.5-pro"):
        """Initialize the Gemini API client.
        
        Args:
            model_name: Name of the Gemini model to use
            
        Raises:
            ValueError: If GOOGLE_AI_STUDIO_API_KEY is not set or model initialization fails
        """
        api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_AI_STUDIO_API_KEY environment variable is not set. "
                "Please set it before using the GeminiAnalysisClient."
            )
        
        # Configure API key
        genai.configure(api_key=api_key)
        
        try:
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini model: {str(e)}")
    
    def _create_analysis_prompt(self) -> str:
        """Create the prompt for Gemini API gesture and posture analysis.
        
        Returns:
            Prompt string for analysis
        """
        return """Analyze the speaker's gestures and body posture in this video segment. 
Provide a detailed analysis in JSON format with the following structure:

{
  "gesture_analysis": {
    "hand_movements": {
      "frequency": "low/medium/high",
      "types_identified": ["list", "of", "gesture", "types"],
      "effectiveness_score": 1-10,
      "observations": ["specific observations about hand movements"]
    },
    "gesture_variety": 1-10,
    "gesture_timing": "well-timed/poorly-timed/mixed"
  },
  "posture_analysis": {
    "stance": "open/closed/neutral",
    "body_alignment": "good/fair/poor",
    "posture_score": 1-10,
    "confidence_indicators": ["list of confidence indicators"],
    "observations": ["specific observations about posture"]
  },
  "coordination": {
    "gesture_posture_alignment": 1-10,
    "overall_coherence": "description"
  },
  "segment_score": 1-10,
  "strengths": ["list of strengths"],
  "weaknesses": ["list of weaknesses"]
}

Focus on:
1. Hand movements: pointing, open palms, closed fists, hand positions, gesture frequency and clarity
2. Body posture: stance (open/closed), shoulder position, body alignment, leaning, balance
3. Effectiveness: how well gestures support the message, posture confidence, overall presentation quality

Provide specific, actionable observations and rate each aspect on a scale of 1-10."""
    
    def _extract_frames(self, video_path: str, max_frames: int = 8) -> List:
        """Extract representative frames from the video."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # Default to 30 FPS if unavailable
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0

        if total_frames > 0:
            frame_interval = max(1, int(total_frames / max_frames))
            frames_to_analyze = min(max_frames, int(total_frames / frame_interval) or 1)
        else:
            frame_interval = int(fps * 1.5) or 1
            frames_to_analyze = max_frames
        
        frames = []
        frame_count = 0
        while frame_count < frames_to_analyze:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert BGR to RGB for Gemini
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)
            frame_count += 1
            
            # Skip frames to sample evenly
            for _ in range(frame_interval - 1):
                if frame_count >= frames_to_analyze:
                    break
                cap.read()
        
        cap.release()
        return frames
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from Gemini API.
        
        Args:
            response_text: Raw response text from Gemini
            
        Returns:
            Parsed analysis dictionary
        """
        try:
            # Look for JSON in the response (handle markdown code blocks)
            json_start = response_text.find('{')
            if json_start == -1:
                json_start = response_text.find('```json') + 7
                if json_start < 7:
                    json_start = response_text.find('```') + 3
            
            json_end = response_text.rfind('}') + 1
            if json_end == 0:
                json_end = response_text.rfind('```')
                if json_end > 0:
                    json_end = response_text.rfind('}', 0, json_end) + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end].strip()
                # Remove markdown code block markers if present
                json_str = json_str.strip('`').strip()
                return json.loads(json_str)
            else:
                # Fallback: create structured response from text
                return self._parse_text_response(response_text)
        except json.JSONDecodeError as json_error:
            # If JSON parsing fails, parse the text response
            print(f"Warning: JSON parsing failed, using text parser: {json_error}")
            return self._parse_text_response(response_text)
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response from Gemini when JSON parsing fails.
        
        Args:
            text: Response text from Gemini
            
        Returns:
            Dictionary with parsed analysis
        """
        # Extract scores and key information from text
        # This is a fallback parser
        return {
            "gesture_analysis": {
                "hand_movements": {
                    "frequency": "medium",
                    "types_identified": [],
                    "effectiveness_score": 5,
                    "observations": [text[:200]]  # First 200 chars as observation
                },
                "gesture_variety": 5,
                "gesture_timing": "mixed"
            },
            "posture_analysis": {
                "stance": "neutral",
                "body_alignment": "fair",
                "posture_score": 5,
                "confidence_indicators": [],
                "observations": [text[:200]]
            },
            "coordination": {
                "gesture_posture_alignment": 5,
                "overall_coherence": "average"
            },
            "segment_score": 5,
            "strengths": [],
            "weaknesses": []
        }
    
    def analyze_entire_video(self, video_path: str) -> Dict[str, Any]:
        """Analyze an entire video using the Gemini API."""

        video_file = None
        try:
            # Extract key frames from the segment for analysis
            frames = self._extract_frames(video_path)
            
            # Create analysis prompt with segment context
            prompt = self._create_analysis_prompt()
            prompt += "\n\nAnalyze the speaker throughout the entire video. "
            prompt += "Summarize overall gesture and posture patterns."
            
            if frames:
                # Use sampled frames for analysis (preferred method)
                try:
                    images = [Image.fromarray(frame) for frame in frames]
                    response = self.model.generate_content([prompt, *images])
                except Exception as frame_error:
                    print(f"Warning: Frame analysis failed, using full video: {frame_error}")
                    video_file = genai.upload_file(path=video_path)
                    response = self.model.generate_content([prompt, video_file])
                    if video_file:
                        video_file.delete()
                        video_file = None
            else:
                # Fallback: analyze the full video with time range context
                video_file = genai.upload_file(path=video_path)
                response = self.model.generate_content([prompt, video_file])
                video_file.delete()
                video_file = None
            
            # Parse response
            if not response or not hasattr(response, 'text') or not response.text:
                raise ValueError("Empty response from Gemini API")
            
            response_text = response.text
            analysis_json = self._parse_response(response_text)
            
            # Ensure required fields exist
            if 'gesture_analysis' not in analysis_json:
                analysis_json['gesture_analysis'] = {}
            if 'posture_analysis' not in analysis_json:
                analysis_json['posture_analysis'] = {}
            if 'segment_score' not in analysis_json:
                analysis_json['segment_score'] = 0
            
            analysis_json.setdefault(
                'video_metadata',
                {
                    'video_path': video_path,
                },
            )
            
            return analysis_json
            
        except Exception as e:
            # Clean up video file if it exists
            if video_file:
                try:
                    video_file.delete()
                except:
                    pass
            
            # Return error structure
            error_msg = str(e)
            print(f"Error analyzing video: {error_msg}")
            
            return {
                'error': error_msg,
                'gesture_analysis': {
                    'hand_movements': {
                        'effectiveness_score': 0,
                        'observations': [f"Analysis failed: {error_msg}"]
                    }
                },
                'posture_analysis': {
                    'posture_score': 0,
                    'observations': [f"Analysis failed: {error_msg}"]
                },
                'segment_score': 0,
                'strengths': [],
                'weaknesses': []
            }

