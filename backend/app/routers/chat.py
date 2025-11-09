from fastapi import APIRouter, HTTPException
import logging

from app.services.chat import FeedbackChat
from app.models import ChatStartRequest, ChatStartResponse, ChatMessageRequest, ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

chat_service = FeedbackChat()

@router.post("/start", response_model=ChatStartResponse)
async def start_chat(request: ChatStartRequest):
    """
    Start a new chat conversation with the provided feedback JSON.
    
    Call this after receiving analysis results to enable Q&A about the feedback.
    """
    try:
        conversation_id = chat_service.start_conversation(request.feedback_json)
        return ChatStartResponse(
            conversation_id=conversation_id,
            message="Conversation started. Ask me anything about your feedback!"
        )
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest):
    """
    Send a message in an existing conversation.
    
    The assistant will answer based strictly on the feedback JSON provided when starting the chat.
    """
    try:
        reply = await chat_service.send_message(
            request.conversation_id,
            request.user_message
        )
        return ChatMessageResponse(assistant_reply=reply)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
