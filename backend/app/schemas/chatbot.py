from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class ChatMessageCreate(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: int
    farmer_id: int
    title: str
    created_at: Optional[datetime] = None
    messages: Optional[List[ChatMessageResponse]] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    id: int
    farmer_id: int
    title: str
    created_at: Optional[datetime] = None
    message_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
