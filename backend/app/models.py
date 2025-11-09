from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# Request models
class AnalyzeRequest(BaseModel):
    video_path: str = Field(..., description="Path to uploaded video file")
    audio_path: Optional[str] = Field(None, description="Optional separate audio file")

class ChatStartRequest(BaseModel):
    feedback_json: dict = Field(..., description="The complete feedback JSON from analysis")

class ChatMessageRequest(BaseModel):
    conversation_id: str
    user_message: str

# Response models
class TimestampedFeedback(BaseModel):
    time_range: str
    details: List[str]

class SubCategoryFeedback(BaseModel):
    effectiveness_score: int = Field(..., ge=1, le=100)
    overall_feedback: str
    observations: List[str]
    timestamped_feedback: List[TimestampedFeedback]

class FillerWordSubCategory(SubCategoryFeedback):
    filler_word_counts: Dict[str, int]

class NonVerbalFeedback(BaseModel):
    eye_contact: SubCategoryFeedback
    gestures: SubCategoryFeedback
    posture: SubCategoryFeedback

class DeliveryFeedback(BaseModel):
    clarity_enunciation: SubCategoryFeedback
    intonation: SubCategoryFeedback
    eloquence_filler_words: FillerWordSubCategory

class ContentFeedback(BaseModel):
    organization_flow: SubCategoryFeedback
    persuasiveness_impact: SubCategoryFeedback
    clarity_of_message: SubCategoryFeedback

class OverallFeedback(BaseModel):
    summary: str
    strengths: List[str]
    areas_to_improve: List[str]
    prioritized_actions: List[str]

class FeedbackResponse(BaseModel):
    non_verbal: NonVerbalFeedback
    delivery: DeliveryFeedback
    content: ContentFeedback
    overall_feedback: OverallFeedback

class ChatStartResponse(BaseModel):
    conversation_id: str
    message: str

class ChatMessageResponse(BaseModel):
    assistant_reply: str
