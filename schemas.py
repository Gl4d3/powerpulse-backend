from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class MessageCreate(BaseModel):
    fb_chat_id: str
    message_content: str
    direction: str = Field(..., pattern="^(to_company|to_client)$")
    social_create_time: datetime
    agent_info: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    id: int
    fb_chat_id: str
    message_content: str
    direction: str
    social_create_time: datetime
    agent_info: Optional[Dict[str, Any]]
    sentiment_score: Optional[float]
    sentiment_confidence: Optional[float]
    topics: Optional[List[str]]
    is_first_contact: bool
    response_time_minutes: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    fb_chat_id: str
    total_messages: int
    customer_messages: int
    agent_messages: int
    satisfaction_score: Optional[float]
    satisfaction_confidence: Optional[float]
    is_satisfied: Optional[bool]
    avg_sentiment: Optional[float]
    first_contact_resolution: bool
    avg_response_time_minutes: Optional[float]
    first_message_time: Optional[datetime]
    last_message_time: Optional[datetime]
    common_topics: Optional[List[str]]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class MetricsResponse(BaseModel):
    avg_sentiment_score: float
    csat_percentage: float
    fcr_percentage: float
    avg_response_time_minutes: float
    total_conversations: int
    total_messages: int
    most_common_topics: List[Dict[str, Any]]
    last_updated: datetime

class UploadResponse(BaseModel):
    success: bool
    message: str
    conversations_processed: int
    messages_processed: int
    processing_time_seconds: float
    upload_id: Optional[str] = None
    
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class JobBase(BaseModel):
    upload_id: Optional[str] = None
    status: Optional[str] = "pending"

class JobCreate(JobBase):
    conversation_ids: List[int]

class JobUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None

class JobResponse(JobBase):
    id: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    conversations: List[ConversationResponse] = []

    class Config:
        from_attributes = True

class ProgressStatistics(BaseModel):
    filtered_autoresponses: int
    gpt_calls_made: int
    errors_count: int

class ProgressResponse(BaseModel):
    upload_id: str
    status: str
    progress_percentage: float
    current_stage: str
    processed_conversations: int
    total_conversations: int
    details: str
    start_time: datetime
    last_update: datetime
    duration_seconds: float
    statistics: ProgressStatistics
    errors: List[str]
