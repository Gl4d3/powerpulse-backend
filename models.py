from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

job_conversations = Table('job_conversations', Base.metadata,
    Column('job_id', Integer, ForeignKey('jobs.id'), primary_key=True),
    Column('conversation_id', Integer, ForeignKey('conversations.id'), primary_key=True)
)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String, index=True) # To associate jobs with a specific upload
    status = Column(String, default="pending", index=True) # pending, in_progress, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSON, nullable=True)

    conversations = relationship("Conversation", secondary=job_conversations, back_populates="jobs")

# This file defines the SQLAlchemy ORM models for the PowerPulse application,
# mapping Python classes to database tables. It includes models for Jobs,
# Conversations, Messages, Processed Chats, and cached Metrics, forming the
# core data structure of the application.

class Conversation(Base):
    """
    Represents a single customer conversation, storing both raw data and the
    results of the AI analysis, including the new Customer Satisfaction Index (CSI).
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    fb_chat_id = Column(String, unique=True, index=True, nullable=False)
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    # Aggregated metrics
    total_messages = Column(Integer, default=0)
    customer_messages = Column(Integer, default=0)
    agent_messages = Column(Integer, default=0)
    
    # --- Legacy Satisfaction Analysis (to be deprecated) ---
    satisfaction_score = Column(Float, nullable=True)
    satisfaction_confidence = Column(Float, nullable=True)
    is_satisfied = Column(Boolean, nullable=True)
    
    # --- New Customer Satisfaction Index (CSI) ---
    # Micro-Metric Scores (from AI)
    resolution_achieved = Column(Float, nullable=True)
    fcr_score = Column(Float, nullable=True)
    response_time_score = Column(Float, nullable=True)
    customer_effort_score = Column(Float, nullable=True)
    
    # Pillar scores (Calculated from Micro-metrics)
    effectiveness_score = Column(Float, nullable=True)
    efficiency_score = Column(Float, nullable=True)
    effort_score = Column(Float, nullable=True)
    empathy_score = Column(Float, nullable=True)
    
    # Final weighted score
    csi_score = Column(Float, nullable=True, index=True)
    
    # Metrics
    avg_sentiment = Column(Float, nullable=True)
    first_contact_resolution = Column(Boolean, default=False)
    avg_response_time_minutes = Column(Float, nullable=True)
    
    # Metadata
    first_message_time = Column(DateTime, nullable=True)
    last_message_time = Column(DateTime, nullable=True)
    common_topics = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    jobs = relationship("Job", secondary=job_conversations, back_populates="conversations")

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
