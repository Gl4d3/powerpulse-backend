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
    """
    Schema for representing a single chat message, used in conversation transcripts.
    This model is used to structure the output of individual messages for the frontend.
    """
    timestamp: datetime = Field(..., alias='social_create_time')
    direction: str
    content: str = Field(..., alias='message_content')
    sentiment_score: Optional[float] = None
    topics: Optional[List[str]] = None
    agent_info: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class DailyAnalysisResponse(BaseModel):
    daily_analysis_id: int
    conversation_id: str
    customer_name: Optional[str] = None
    analysis_date: date
    
    # CONSTITUTIONAL DUAL CSI EXPOSURE
    csi_score: Optional[float] = None  # Primary CSI (calculated from AI micro-metrics → four pillars)
    inferred_csi: Optional[float] = None  # AI blackbox CSI (for comparison/validation)
    
    # Four-pillars scores (from AI micro-metrics)
    effectiveness_score: Optional[float] = None
    efficiency_score: Optional[float] = None
    effort_score: Optional[float] = None
    empathy_score: Optional[float] = None
    common_topics: Optional[List[str]] = None
    agents: List[Dict[str, Any]] = []
    conversation_duration: Optional[float] = None
    sentiment_score: Optional[float] = None
    sentiment_shift: Optional[float] = None
    resolution_achieved: Optional[float] = None
    fcr_score: Optional[float] = None
    ces: Optional[float] = None
    first_response_time: Optional[float] = None
    avg_response_time: Optional[float] = None
    total_handling_time: Optional[float] = None

    total_messages: Optional[int] = None
    customer_messages: Optional[int] = None
    agent_messages: Optional[int] = None

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    """
    Represents an aggregated summary of a conversation for the frontend.
    This model provides a consolidated view of a conversation's metrics, calculated
    by averaging all of its associated DailyAnalysis records.
    """
    chat_id: str
    username: Optional[str] = None
    avg_csi_score: Optional[float] = None
    avg_effectiveness_score: Optional[float] = None
    avg_efficiency_score: Optional[float] = None
    avg_effort_score: Optional[float] = None
    avg_empathy_score: Optional[float] = None
    topics: List[str] = []
    agents: List[dict] = []
    created_at: Optional[datetime] = None
    
    # Message statistics
    total_messages: Optional[int] = None
    customer_messages: Optional[int] = None
    agent_messages: Optional[int] = None
    first_message_time: Optional[datetime] = None
    last_message_time: Optional[datetime] = None
    
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
    Updated to include all micro-metrics and current calculated metrics.
    """
    # CSI and pillars (0-100 scale for frontend)
    csi: float
    resolution_quality: float  # effectiveness_score * 10
    service_timeliness: float  # efficiency_score * 10
    customer_ease: float       # effort_score * 10
    interaction_quality: float # empathy_score * 10
    
    # Micro-metrics used to calculate the pillars
    sentiment_score: float           # Average sentiment score
    sentiment_shift: float           # Average sentiment shift
    resolution_achieved: float       # Average resolution achieved score
    fcr_score: float                # Average first call resolution score
    ces: float                      # Average customer effort score
    first_response_time: float      # Average first response time (seconds)
    avg_response_time: float        # Average response time (seconds)
    total_handling_time: float      # Average total handling time (minutes)
    
    # Sample and metadata
    sample_count: int
    
    # Deltas and metadata
    deltas: Optional[Dict[str, float]] = None
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


# --- Job Management Schemas ---

class JobStatusResponse(BaseModel):
    """A lightweight response for listing jobs."""
    id: int
    status: str
    task_name: Optional[str] = None
    upload_id: Optional[str] = None
    retry_count: int
    created_at: datetime
    run_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobDetailsResponse(JobStatusResponse):
    """A detailed response for a single job, including errors and results."""
    last_error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class PaginatedJobResponse(BaseModel):
    pagination: Pagination
    data: List[JobStatusResponse]

class JobRetryResponse(BaseModel):
    job_id: int
    new_status: str
    message: str

# Interaction-based analysis schemas
class InteractionAnalysisResponse(BaseModel):
    """Response schema for individual interaction analysis results."""
    interaction_id: int
    conversation_id: str
    customer_name: Optional[str] = None
    interaction_start: datetime
    interaction_end: datetime
    
    # CONSTITUTIONAL DUAL CSI EXPOSURE
    csi_score: Optional[float] = None  # Primary CSI (calculated from AI micro-metrics → four pillars)
    inferred_csi: Optional[float] = None  # AI blackbox CSI (for comparison/validation)
    
    # Four-pillars scores (from AI micro-metrics)
    effectiveness_score: Optional[float] = None
    efficiency_score: Optional[float] = None
    effort_score: Optional[float] = None
    empathy_score: Optional[float] = None
    
    # Interaction-specific metrics
    interaction_type: Optional[str] = None
    interaction_complexity: Optional[str] = None
    interaction_duration: Optional[float] = None  # in minutes
    message_count: Optional[int] = None
    turns_count: Optional[int] = None
    
    # Detailed micro-metrics
    sentiment_score: Optional[float] = None
    sentiment_shift: Optional[float] = None
    resolution_achieved: Optional[float] = None
    fcr_score: Optional[float] = None
    ces: Optional[float] = None
    first_response_time: Optional[float] = None
    avg_response_time: Optional[float] = None
    total_handling_time: Optional[float] = None
    
    # Context
    common_topics: Optional[List[str]] = None
    agents: List[Dict[str, Any]] = []
    
    class Config:
        from_attributes = True

class InteractionMetricsResponse(BaseModel):
    """
    Response model for interaction-based CSI metrics, mirroring CSIMetricsResponse
    but with interaction-specific aggregations.
    """
    # CSI and pillars (0-100 scale for frontend)
    csi: float
    resolution_quality: float  # effectiveness_score * 10
    service_timeliness: float  # efficiency_score * 10
    customer_ease: float       # effort_score * 10
    interaction_quality: float # empathy_score * 10
    
    # Micro-metrics used to calculate the pillars
    sentiment_score: float           # Average sentiment score
    sentiment_shift: float           # Average sentiment shift
    resolution_achieved: float       # Average resolution achieved score
    fcr_score: float                # Average first call resolution score
    ces: float                      # Average customer effort score
    first_response_time: float      # Average first response time (seconds)
    avg_response_time: float        # Average response time (seconds)
    total_handling_time: float      # Average total handling time (minutes)
    
    # Interaction-specific aggregations
    avg_interaction_duration: float  # Average interaction duration (minutes)
    avg_message_count: float        # Average messages per interaction
    avg_turns_count: float          # Average turns per interaction
    
    # Sample and metadata
    sample_count: int
    interaction_count: int          # Total interactions analyzed
    
    # Deltas and metadata
    deltas: Optional[Dict[str, float]] = None
    pillar_weights: Dict[str, float]
    
    # Interaction distribution
    interaction_complexity_distribution: Optional[Dict[str, int]] = None

class InteractionHistoricalMetricsResponse(BaseModel):
    """Container for a list of interaction metrics over a date range."""
    data: List[InteractionAnalysisResponse]

class InteractionConversationResponse(BaseModel):
    """
    Response model for conversations with interaction-based aggregations.
    """
    chat_id: str
    username: Optional[str] = None
    
    # Interaction-aggregated scores
    avg_csi_score: Optional[float] = None
    avg_effectiveness_score: Optional[float] = None
    avg_efficiency_score: Optional[float] = None
    avg_effort_score: Optional[float] = None
    avg_empathy_score: Optional[float] = None
    
    # Interaction statistics
    total_interactions: int
    avg_interaction_duration: Optional[float] = None
    most_common_interaction_type: Optional[str] = None
    complexity_distribution: Optional[Dict[str, int]] = None
    
    # Conversation metadata (unchanged)
    topics: List[str] = []
    agents: List[Dict[str, Any]] = []
    created_at: Optional[datetime] = None
    total_messages: Optional[int] = None
    customer_messages: Optional[int] = None
    agent_messages: Optional[int] = None
    first_message_time: Optional[datetime] = None
    last_message_time: Optional[datetime] = None

class InteractionConversationListResponse(BaseModel):
    """Paginated response for interaction-based conversation list."""
    conversations: List[InteractionConversationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
