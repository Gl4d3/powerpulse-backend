from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

job_daily_analyses = Table('job_daily_analyses', Base.metadata,
    Column('job_id', Integer, ForeignKey('jobs.id'), primary_key=True),
    Column('daily_analysis_id', Integer, ForeignKey('daily_analyses.id'), primary_key=True)
)

job_interaction_analyses = Table('job_interaction_analyses', Base.metadata,
    Column('job_id', Integer, ForeignKey('jobs.id'), primary_key=True),
    Column('interaction_analysis_id', Integer, ForeignKey('interaction_analyses.id'), primary_key=True)
)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)  # Changed to String for UUID support
    upload_id = Column(String, index=True, nullable=True) # Legacy support for old uploads
    session_id = Column(String, ForeignKey("upload_sessions.session_id"), nullable=True, index=True)  # New session support
    
    # Core job metadata
    task_name = Column(String, nullable=True, default="default_csi_analysis")
    job_type = Column(String, nullable=True, index=True)  # interaction_analysis, interaction_analysis_batch, etc.
    status = Column(String, default="pending", index=True) # pending, queued, running, completed, failed, cancelled, retryable_failure
    priority = Column(Integer, default=0, nullable=False, index=True)  # Job priority for queue ordering
    
    # Execution and retry logic
    run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Enhanced payload and context
    payload = Column(JSON, nullable=True)  # Job-specific data and configuration
    context = Column(JSON, nullable=True)  # Execution context and metadata
    
    # Constitutional compliance tracking
    constitutional_compliance_required = Column(Boolean, default=True, nullable=False)
    ai_supremacy_validated = Column(Boolean, default=False, nullable=False)
    dual_csi_validated = Column(Boolean, default=False, nullable=False)
    
    # Performance and cost tracking
    estimated_processing_time = Column(Float, nullable=True)  # Estimated time in seconds
    actual_processing_time = Column(Float, nullable=True)  # Actual time in seconds
    cost_optimization_target = Column(Float, nullable=True)  # Target cost reduction percentage
    cost_optimization_achieved = Column(Float, nullable=True)  # Actual cost reduction achieved
    
    # Timestamps and results
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    last_error = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)

    # Relationships
    upload_session = relationship("UploadSession", back_populates="jobs")
    daily_analyses = relationship("DailyAnalysis", secondary=job_daily_analyses, back_populates="jobs")
    interaction_analyses = relationship("InteractionAnalysis", secondary=job_interaction_analyses, back_populates="jobs")
    job_metrics = relationship("JobMetric", back_populates="job", cascade="all, delete-orphan")
    
    # Enhanced indexes
    __table_args__ = (
        Index('idx_job_status_priority', 'status', 'priority', 'created_at'),
        Index('idx_job_session_type', 'session_id', 'job_type'),
        Index('idx_job_constitutional', 'constitutional_compliance_required', 'ai_supremacy_validated', 'dual_csi_validated'),
        Index('idx_job_performance', 'actual_processing_time', 'cost_optimization_achieved'),
    )

class JobMetric(Base):
    __tablename__ = 'job_metrics'
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    job = relationship("Job", back_populates="job_metrics")
    token_usage = Column(Integer)
    processing_time_seconds = Column(Float)
    api_calls_made = Column(Integer, default=1)
    api_calls_made = Column(Integer, default=1)


# class ProgressUpdate(Base):
#     __tablename__ = 'progress_updates'
#     upload_id = Column(String, primary_key=True)
#     filename = Column(String, nullable=False)
#     status = Column(String, default='processing')
#     total_conversations = Column(Integer, default=0)
#     processed_conversations = Column(Integer, default=0)
#     progress_percentage = Column(Float, default=0.0)
#     current_stage = Column(String, default='initializing')
#     start_time = Column(DateTime, default=datetime.utcnow)
#     last_update = Column(DateTime, default=datetime.utcnow)
#     end_time = Column(DateTime, nullable=True)
#     last_error = Column(Text, nullable=True)



# This file defines the SQLAlchemy ORM models for the PowerPulse application,
# mapping Python classes to database tables. It includes models for Jobs,
# Conversations, Messages, Processed Chats, and cached Metrics, forming the
# core data structure of the application.

class Conversation(Base):
    """
    Represents a single customer conversation, storing overall metadata.
    The detailed analysis is stored in DailyAnalysis (legacy) and InteractionAnalysis (new) models.
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    fb_chat_id = Column(String, unique=True, index=True, nullable=False)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    daily_analyses = relationship("DailyAnalysis", back_populates="conversation", cascade="all, delete-orphan")
    interaction_analyses = relationship("InteractionAnalysis", back_populates="conversation", cascade="all, delete-orphan")

    # Overall aggregated metrics
    total_messages = Column(Integer, default=0)
    customer_messages = Column(Integer, default=0)
    agent_messages = Column(Integer, default=0)
    customer_name = Column(String, nullable=True) # New field for customer's name
    
    # Metadata
    first_message_time = Column(DateTime, nullable=True)
    last_message_time = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DailyAnalysis(Base):
    """
    Stores the detailed CSI analysis for a single day within a conversation.
    """
    __tablename__ = "daily_analyses"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    analysis_date = Column(DateTime, nullable=False)

    conversation = relationship("Conversation", back_populates="daily_analyses")
    jobs = relationship("Job", secondary=job_daily_analyses, back_populates="daily_analyses")

    # --- Micro-Metrics (from AI or calculated) ---
    sentiment_score = Column(Float, nullable=True)
    sentiment_shift = Column(Float, nullable=True)
    resolution_achieved = Column(Float, nullable=True)
    fcr_score = Column(Float, nullable=True)
    ces = Column(Float, nullable=True) # Customer Effort Score
    common_topics = Column(JSON, nullable=True)
    first_response_time = Column(Float, nullable=True) # seconds
    avg_response_time = Column(Float, nullable=True) # seconds
    total_handling_time = Column(Float, nullable=True) # minutes

    # --- Pillar Scores (Calculated from Micro-metrics) ---
    effectiveness_score = Column(Float, nullable=True)
    effort_score = Column(Float, nullable=True)
    efficiency_score = Column(Float, nullable=True)
    empathy_score = Column(Float, nullable=True)

    # --- Final CSI Score for the Day ---
    csi_score = Column(Float, nullable=True, index=True)

    __table_args__ = (
        Index('idx_conversation_date', 'conversation_id', 'analysis_date', unique=True),
    )


class InteractionAnalysis(Base):
    """
    Stores CSI analysis for individual customer service interactions within conversations.
    Unlike DailyAnalysis, this allows multiple interactions per day and tracks interaction boundaries.
    """
    __tablename__ = "interaction_analyses"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    
    # Message Range
    start_message_id = Column(Integer, nullable=False)   # First message in interaction
    end_message_id = Column(Integer, nullable=False)     # Last message in interaction
    
    # Interaction Boundaries
    interaction_start = Column(DateTime, nullable=False)  # First message timestamp
    interaction_end = Column(DateTime, nullable=False)    # Last message timestamp  
    interaction_type = Column(String, nullable=True)     # "outage", "billing", "inquiry", etc.
    interaction_duration = Column(Float, nullable=True)  # Duration in minutes
    interaction_complexity = Column(String, nullable=True) # "simple", "moderate", "complex"
    
    # Interaction Statistics
    message_count = Column(Integer, nullable=True)       # Total messages in interaction
    turns_count = Column(Integer, nullable=True)         # Number of conversation turns
    
    # Detection Metadata
    boundary_method = Column(String, nullable=False)     # "time_gap", "resolution_keywords", "ai_detected"
    boundary_confidence = Column(Float, nullable=True)   # 0.0-1.0 confidence score
    
    # Relationships
    conversation = relationship("Conversation", back_populates="interaction_analyses")
    jobs = relationship("Job", secondary=job_interaction_analyses, back_populates="interaction_analyses")

    # --- Micro-Metrics (Identical to DailyAnalysis) ---
    sentiment_score = Column(Float, nullable=True)        # 0-10 scale
    sentiment_shift = Column(Float, nullable=True)        # -5 to +5
    resolution_achieved = Column(Float, nullable=True)    # 0-10 scale
    fcr_score = Column(Float, nullable=True)             # 0-10 scale
    ces = Column(Float, nullable=True)                   # 1-7 scale (Customer Effort Score)
    common_topics = Column(JSON, nullable=True)          # Array of topic strings
    first_response_time = Column(Float, nullable=True)   # seconds
    avg_response_time = Column(Float, nullable=True)     # seconds
    total_handling_time = Column(Float, nullable=True)   # minutes

    # --- Pillar Scores (Calculated from Micro-metrics) ---
    effectiveness_score = Column(Float, nullable=True)   # 0-10 scale
    effort_score = Column(Float, nullable=True)         # 0-10 scale
    efficiency_score = Column(Float, nullable=True)     # 0-10 scale
    empathy_score = Column(Float, nullable=True)        # 0-10 scale

    # --- Final CSI Score for the Interaction ---
    csi_score = Column(Float, nullable=True, index=True) # 0-10 scale (calculated from four-pillars)
    inferred_csi = Column(Float, nullable=True)          # 0-10 scale (AI blackbox inference)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_conversation_interaction_start', 'conversation_id', 'interaction_start'),
        Index('idx_interaction_message_range', 'start_message_id', 'end_message_id'),
        Index('idx_boundary_method', 'boundary_method'),
    )


class Message(Base):
    """Individual message records with sentiment analysis"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    fb_chat_id = Column(String, index=True, nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    message_content = Column(Text, nullable=False)
    direction = Column(String, nullable=False)  # 'to_company' or 'to_client'
    social_create_time = Column(DateTime, nullable=False)
    agent_info = Column(JSON, nullable=True)
    conversation = relationship("Conversation", back_populates="messages")
    
    # Analysis results
    sentiment_score = Column(Float, nullable=True)  # 1-5 scale
    sentiment_confidence = Column(Float, nullable=True)  # 0-1 scale
    topics = Column(JSON, nullable=True)  # Array of extracted topics
    
    # Metrics
    is_first_contact = Column(Boolean, default=False)
    response_time_minutes = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_fb_chat_direction', 'fb_chat_id', 'direction'),
        Index('idx_social_create_time', 'social_create_time'),
    )



class Metric(Base):
    """Cached aggregated metrics for quick dashboard loading"""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, unique=True, index=True, nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_metadata = Column(JSON, nullable=True)  # Additional context
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UploadSession(Base):
    """
    Upload session for batch processing with constitutional compliance.
    Tracks session lifecycle, file metadata, and processing status.
    """
    __tablename__ = "upload_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    filename = Column(String, nullable=False)
    user_id = Column(String, nullable=True, index=True)
    
    # Processing status and metrics
    status = Column(String, default="initialized", index=True)  # initialized, processing, completed, failed, partial_success, cancelled
    total_interactions = Column(Integer, default=0, nullable=False)
    processed_interactions = Column(Integer, default=0, nullable=False)
    failed_interactions = Column(Integer, default=0, nullable=False)
    
    # Constitutional compliance tracking
    ai_micro_metrics_enabled = Column(Boolean, default=True, nullable=False)
    dual_csi_architecture = Column(Boolean, default=True, nullable=False)
    batch_optimization_enabled = Column(Boolean, default=True, nullable=False)
    
    # Performance metrics
    processing_time = Column(Float, nullable=True)  # Total processing time in seconds
    cost_reduction_achieved = Column(Float, nullable=True)  # Percentage cost reduction
    processing_speed = Column(Float, nullable=True)  # Interactions per second
    
    # Metadata and error tracking
    session_metadata = Column(JSON, nullable=True)  # User-provided metadata
    processing_summary = Column(JSON, nullable=True)  # Final processing results
    error_details = Column(JSON, nullable=True)  # Error information
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    batch_contexts = relationship("BatchContext", back_populates="upload_session", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="upload_session", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_session_status_created', 'status', 'created_at'),
        Index('idx_user_sessions', 'user_id', 'created_at'),
        Index('idx_session_performance', 'processing_speed', 'cost_reduction_achieved'),
    )


class BatchContext(Base):
    """
    Individual batch context within an upload session.
    Tracks batch-level processing, optimization, and constitutional compliance.
    """
    __tablename__ = "batch_contexts"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, unique=True, index=True, nullable=False)
    session_id = Column(String, ForeignKey("upload_sessions.session_id"), nullable=False)
    
    # Batch organization
    batch_index = Column(Integer, nullable=False)  # Order within session (0-based)
    interactions_count = Column(Integer, default=0, nullable=False)
    
    # Processing status
    status = Column(String, default="pending", index=True)  # pending, processing, completed, failed, cancelled, retrying
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Constitutional compliance per batch
    ai_supremacy_enforced = Column(Boolean, default=True, nullable=False)
    dual_csi_validated = Column(Boolean, default=True, nullable=False)
    cost_optimization_applied = Column(Boolean, default=True, nullable=False)
    
    # Performance metrics per batch
    processing_time = Column(Float, nullable=True)  # Processing time in seconds
    api_calls_made = Column(Integer, default=0, nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    cost_reduction_achieved = Column(Float, nullable=True)  # Percentage for this batch
    
    # Data storage
    interactions_data = Column(JSON, nullable=True)  # Raw interaction data for batch
    result_data = Column(JSON, nullable=True)  # Processed results and metrics
    error_details = Column(JSON, nullable=True)  # Batch-specific error information
    
    # Optimization context
    optimization_strategy = Column(JSON, nullable=True)  # Strategy applied to this batch
    gemini_prompt_used = Column(Text, nullable=True)  # Prompt template used
    context_window_usage = Column(Float, nullable=True)  # Percentage of context window used
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    upload_session = relationship("UploadSession", back_populates="batch_contexts")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_session_batch_order', 'session_id', 'batch_index'),
        Index('idx_batch_status_created', 'status', 'created_at'),
        Index('idx_batch_performance', 'processing_time', 'cost_reduction_achieved'),
        Index('idx_constitutional_compliance', 'ai_supremacy_enforced', 'dual_csi_validated'),
    )
