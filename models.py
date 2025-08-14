from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class ProcessedChat(Base):
    """Track which chat IDs have been processed to avoid reprocessing"""
    __tablename__ = "processed_chats"
    
    id = Column(Integer, primary_key=True, index=True)
    fb_chat_id = Column(String, unique=True, index=True, nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    message_count = Column(Integer, default=0)
    
class Message(Base):
    """Individual message records with sentiment analysis"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    fb_chat_id = Column(String, index=True, nullable=False)
    message_content = Column(Text, nullable=False)
    direction = Column(String, nullable=False)  # 'to_company' or 'to_client'
    social_create_time = Column(DateTime, nullable=False)
    agent_info = Column(JSON, nullable=True)
    
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

class Conversation(Base):
    """Conversation-level aggregated data and satisfaction analysis"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    fb_chat_id = Column(String, unique=True, index=True, nullable=False)
    
    # Aggregated metrics
    total_messages = Column(Integer, default=0)
    customer_messages = Column(Integer, default=0)
    agent_messages = Column(Integer, default=0)
    
    # Satisfaction analysis
    satisfaction_score = Column(Float, nullable=True)  # 1-5 scale
    satisfaction_confidence = Column(Float, nullable=True)  # 0-1 scale
    is_satisfied = Column(Boolean, nullable=True)  # For CSAT calculation
    
    # Metrics
    avg_sentiment = Column(Float, nullable=True)
    first_contact_resolution = Column(Boolean, default=False)
    avg_response_time_minutes = Column(Float, nullable=True)
    
    # Metadata
    first_message_time = Column(DateTime, nullable=True)
    last_message_time = Column(DateTime, nullable=True)
    common_topics = Column(JSON, nullable=True)  # Array of most common topics
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Metric(Base):
    """Cached aggregated metrics for quick dashboard loading"""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, unique=True, index=True, nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_metadata = Column(JSON, nullable=True)  # Additional context
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
