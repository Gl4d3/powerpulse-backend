from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

job_daily_analyses = Table('job_daily_analyses', Base.metadata,
    Column('job_id', Integer, ForeignKey('jobs.id'), primary_key=True),
    Column('daily_analysis_id', Integer, ForeignKey('daily_analyses.id'), primary_key=True)
)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String, index=True) # To associate jobs with a specific upload
    status = Column(String, default="pending", index=True) # pending, in_progress, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSON, nullable=True)

    daily_analyses = relationship("DailyAnalysis", secondary=job_daily_analyses, back_populates="jobs")
    metric = relationship("JobMetric", uselist=False, back_populates="job", cascade="all, delete-orphan")

class JobMetric(Base):
    """
    Stores usage and performance metrics for a single background job.
    """
    __tablename__ = "job_metrics"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, unique=True)
    
    token_usage = Column(Integer, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    api_calls_made = Column(Integer, default=1)

    job = relationship("Job", back_populates="metric")


# This file defines the SQLAlchemy ORM models for the PowerPulse application,
# mapping Python classes to database tables. It includes models for Jobs,
# Conversations, Messages, Processed Chats, and cached Metrics, forming the
# core data structure of the application.

class Conversation(Base):
    """
    Represents a single customer conversation, storing overall metadata.
    The detailed, day-by-day analysis is stored in the DailyAnalysis model.
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    fb_chat_id = Column(String, unique=True, index=True, nullable=False)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    daily_analyses = relationship("DailyAnalysis", back_populates="conversation", cascade="all, delete-orphan")

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

class ProcessedChat(Base):
    """Track which chat IDs have been processed to avoid reprocessing"""
    __tablename__ = "processed_chats"
    
    id = Column(Integer, primary_key=True, index=True)
    fb_chat_id = Column(String, unique=True, index=True, nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    message_count = Column(Integer, default=0)

class Metric(Base):
    """Cached aggregated metrics for quick dashboard loading"""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, unique=True, index=True, nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_metadata = Column(JSON, nullable=True)  # Additional context
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
