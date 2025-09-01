from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date

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

class DailyAnalysisResponse(BaseModel):
    daily_analysis_id: int
    conversation_id: str
    customer_name: Optional[str] = None
    analysis_date: date
    csi_score: Optional[float] = None
    effectiveness_score: Optional[float] = None
    efficiency_score: Optional[float] = None
    effort_score: Optional[float] = None
    empathy_score: Optional[float] = None
    common_topics: Optional[List[str]] = None

    class Config:
        orm_mode = True

    @validator('conversation_id', pre=True, allow_reuse=True)
    def get_fb_chat_id(cls, v, values):
        return values.get('conversation').fb_chat_id

    @validator('customer_name', pre=True, allow_reuse=True)
    def get_customer_name(cls, v, values):
        return values.get('conversation').customer_name

class ConversationResponse(BaseModel):
    """
    Represents an aggregated summary of a conversation for the frontend.
    """
    chat_id: str
    sentiment_score: Optional[float] = None
    satisfaction_score: Optional[float] = None # This will be the aggregated CSI
    fcr: Optional[bool] = None
    topics: List[str] = []
    created_at: datetime
    agent_username: Optional[str] = None
    agent_email: Optional[str] = None
    
    # The detailed daily breakdown can be fetched from a separate endpoint
    # This keeps the main conversation list lightweight.
    
    class Config:
        from_attributes = True

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class CSIMetricsResponse(BaseModel):
    """
    Defines the structure for the aggregated metrics, aligned with the frontend contract.
    """
    # Core KPIs
    sentiment: float
    csat_percentage: float
    fcr_percentage: float
    avg_response_time: float
    sentiment_distribution: Dict[str, float]
    topic_frequency: List[Dict[str, Any]]

    # CSI and pillars (0-100 scale for frontend)
    csi: float
    resolution_quality: float
    service_timeliness: float
    customer_ease: float
    interaction_quality: float
    sample_count: int
    
    # Deltas
    deltas: Optional[Dict[str, float]] = None
    
    # Metadata
    pillar_weights: Dict[str, float]


class LegacyMetricsResponse(BaseModel):
    """Maintains the old metrics structure for backward compatibility."""
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

# --- New Schemas for Historical Analytics ---

class DailyMetricsResponse(BaseModel):
    """Represents the aggregated metrics for a single day."""
    message_timestamp: date
    total_conversations: int
    avg_csi_score: Optional[float] = None
    avg_resolution_achieved: Optional[float] = None
    avg_fcr_score: Optional[float] = None
    avg_response_time_score: Optional[float] = None
    avg_customer_effort_score: Optional[float] = None
    avg_effectiveness_score: Optional[float] = None
    avg_efficiency_score: Optional[float] = None
    avg_effort_score: Optional[float] = None
    avg_empathy_score: Optional[float] = None

class HistoricalMetricsResponse(BaseModel):
    """Container for a list of daily metrics over a date range."""
    data: List[DailyMetricsResponse]

class Pagination(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int

class PaginatedDailyAnalysisResponse(BaseModel):
    pagination: Pagination
    data: List[DailyAnalysisResponse]


class Pagination(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int

class ConversationExplorerResponse(BaseModel):
    daily_analysis_id: int
    conversation_id: str
    customer_name: Optional[str] = None
    analysis_date: date
    csi_score: Optional[float] = None
    effectiveness_score: Optional[float] = None
    efficiency_score: Optional[float] = None
    effort_score: Optional[float] = None
    empathy_score: Optional[float] = None
    common_topics: Optional[List[str]] = None

    class Config:
        orm_mode = True

class PaginatedConversationExplorerResponse(BaseModel):
    pagination: Pagination
    data: List[ConversationExplorerResponse]
