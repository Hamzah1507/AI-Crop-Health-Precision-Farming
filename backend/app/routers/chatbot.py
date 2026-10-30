from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.chatbot import ChatbotConversation, ChatbotMessage
from app.schemas.chatbot import ChatMessageCreate, ChatMessageResponse, ConversationResponse, ConversationListResponse
from app.services.chatbot_service import chatbot_service
from app.utils.deps import get_current_user
from typing import List

router = APIRouter(prefix="/api/chatbot", tags=["AI Agronomist Chatbot"])


@router.post("/message", response_model=ConversationResponse)
def send_message(
    data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to the AI Agronomist chatbot."""
    # Get or create conversation
    if data.conversation_id:
        conversation = db.query(ChatbotConversation).filter(
            ChatbotConversation.id == data.conversation_id,
            ChatbotConversation.farmer_id == current_user.id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation
        title = data.message[:50] + "..." if len(data.message) > 50 else data.message
        conversation = ChatbotConversation(
            farmer_id=current_user.id,
            title=title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Store user message
    user_msg = ChatbotMessage(
        conversation_id=conversation.id,
        role="user",
        content=data.message
    )
    db.add(user_msg)
    db.commit()

    # Get AI response
    ai_response = chatbot_service.get_response(data.message)

    # Store AI message
    ai_msg = ChatbotMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response
    )
    db.add(ai_msg)
    db.commit()

    # Refresh to get all messages
    db.refresh(conversation)

    return conversation


@router.get("/conversations", response_model=List[ConversationListResponse])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations."""
    conversations = (
        db.query(ChatbotConversation)
        .filter(ChatbotConversation.farmer_id == current_user.id)
        .order_by(ChatbotConversation.updated_at.desc())
        .all()
    )
    result = []
    for conv in conversations:
        msg_count = db.query(ChatbotMessage).filter(ChatbotMessage.conversation_id == conv.id).count()
        result.append(ConversationListResponse(
            id=conv.id,
            farmer_id=conv.farmer_id,
            title=conv.title,
            created_at=conv.created_at,
            message_count=msg_count
        ))
    return result


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with messages."""
    conversation = db.query(ChatbotConversation).filter(
        ChatbotConversation.id == conversation_id,
        ChatbotConversation.farmer_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation."""
    conversation = db.query(ChatbotConversation).filter(
        ChatbotConversation.id == conversation_id,
        ChatbotConversation.farmer_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted successfully"}
