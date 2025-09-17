"""
API endpoints for exporting interaction-based analysis data to CSV format.
Provides export capabilities for interaction analyses and associated metrics.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional
import pandas as pd
import io
import logging
from datetime import datetime

from database import get_db
from models import Conversation, Message, InteractionAnalysis
from services.enhanced_analytics_service import enhanced_analytics_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/download")
async def download_interaction_csv(
    db: Session = Depends(get_db),
    export_type: str = Query(default="interactions", pattern="^(interactions|conversations|messages|all)$"),
    min_csi_score: Optional[float] = Query(default=None, ge=1, le=10),
    max_csi_score: Optional[float] = Query(default=None, ge=1, le=10),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    interaction_type: Optional[str] = Query(default=None),
    complexity_level: Optional[str] = Query(default=None)
):
    """
    Export interaction-based analysis data as CSV.
    
    Args:
        export_type: Type of data to export (interactions, conversations, messages, all)
        min_csi_score: Filter by minimum CSI score
        max_csi_score: Filter by maximum CSI score  
        date_from: Start date (YYYY-MM-DD format)
        date_to: End date (YYYY-MM-DD format)
        interaction_type: Filter by interaction type
        complexity_level: Filter by complexity level
    """
    try:
        # Parse date filters if provided
        start_date = None
        end_date = None
        if date_from:
            start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        if date_to:
            end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=400, detail="date_from cannot be after date_to")
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_type == "interactions":
            csv_content = await _export_interactions(
                db, min_csi_score, max_csi_score, start_date, end_date, 
                interaction_type, complexity_level
            )
            filename = f"{timestamp}_interaction_analyses.csv"
            
        elif export_type == "conversations":
            csv_content = await _export_interaction_conversations(
                db, min_csi_score, max_csi_score, start_date, end_date
            )
            filename = f"{timestamp}_interaction_conversations.csv"
            
        elif export_type == "messages":
            csv_content = await _export_interaction_messages(
                db, min_csi_score, max_csi_score, start_date, end_date
            )
            filename = f"{timestamp}_interaction_messages.csv"
            
        elif export_type == "all":
            # Create a zip file with all exports
            interactions_csv = await _export_interactions(
                db, min_csi_score, max_csi_score, start_date, end_date,
                interaction_type, complexity_level
            )
            conversations_csv = await _export_interaction_conversations(
                db, min_csi_score, max_csi_score, start_date, end_date
            )
            messages_csv = await _export_interaction_messages(
                db, min_csi_score, max_csi_score, start_date, end_date
            )
            
            # For simplicity, return interactions CSV with a note
            # In production, you'd want to create a proper zip file
            csv_content = interactions_csv
            filename = f"{timestamp}_all_interaction_data.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error exporting interaction data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error exporting data")

async def _export_interactions(
    db: Session, 
    min_csi: Optional[float], 
    max_csi: Optional[float],
    start_date: Optional[datetime], 
    end_date: Optional[datetime],
    interaction_type: Optional[str],
    complexity_level: Optional[str]
) -> str:
    """Export interaction analyses to CSV format."""
    try:
        # Build query with filters
        query = db.query(InteractionAnalysis).join(Conversation)
        
        if min_csi is not None:
            query = query.filter(InteractionAnalysis.csi_score >= min_csi)
        if max_csi is not None:
            query = query.filter(InteractionAnalysis.csi_score <= max_csi)
        if start_date:
            query = query.filter(InteractionAnalysis.interaction_start >= start_date)
        if end_date:
            query = query.filter(InteractionAnalysis.interaction_end <= end_date)
        if interaction_type:
            query = query.filter(InteractionAnalysis.interaction_type == interaction_type)
        if complexity_level:
            query = query.filter(InteractionAnalysis.interaction_complexity == complexity_level)
        
        interactions = query.all()
        
        # Convert to pandas DataFrame
        data = []
        for interaction in interactions:
            conversation = db.query(Conversation).filter(
                Conversation.id == interaction.conversation_id
            ).first()
            
            data.append({
                'interaction_id': interaction.id,
                'chat_id': conversation.fb_chat_id if conversation else None,
                'customer_name': conversation.customer_name if conversation else None,
                'interaction_start': interaction.interaction_start,
                'interaction_end': interaction.interaction_end,
                'interaction_duration_minutes': interaction.interaction_duration,
                'interaction_type': interaction.interaction_type,
                'interaction_complexity': interaction.interaction_complexity,
                'message_count': interaction.message_count,
                'turns_count': interaction.turns_count,
                'csi_score': interaction.csi_score,
                'effectiveness_score': interaction.effectiveness_score,
                'efficiency_score': interaction.efficiency_score,
                'effort_score': interaction.effort_score,
                'empathy_score': interaction.empathy_score,
                'sentiment_score': interaction.sentiment_score,
                'sentiment_shift': interaction.sentiment_shift,
                'resolution_achieved': interaction.resolution_achieved,
                'fcr_score': interaction.fcr_score,
                'ces': interaction.ces,
                'first_response_time_seconds': interaction.first_response_time,
                'avg_response_time_seconds': interaction.avg_response_time,
                'total_handling_time_minutes': interaction.total_handling_time,
                'common_topics': ', '.join(interaction.common_topics) if interaction.common_topics else None,
                'created_at': interaction.created_at
            })
        
        df = pd.DataFrame(data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error exporting interactions: {e}")
        raise

async def _export_interaction_conversations(
    db: Session,
    min_csi: Optional[float],
    max_csi: Optional[float], 
    start_date: Optional[datetime],
    end_date: Optional[datetime]
) -> str:
    """Export conversation summaries with interaction aggregations."""
    try:
        # Get conversations with interaction aggregations
        conversations_data = enhanced_analytics_service.get_conversations_with_interaction_summary(
            db, min_csi, max_csi, start_date, end_date
        )
        
        # Convert to DataFrame
        df = pd.DataFrame(conversations_data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error exporting interaction conversations: {e}")
        raise

async def _export_interaction_messages(
    db: Session,
    min_csi: Optional[float],
    max_csi: Optional[float],
    start_date: Optional[datetime], 
    end_date: Optional[datetime]
) -> str:
    """Export messages from conversations that have interactions within the criteria."""
    try:
        # Get interaction IDs that match criteria
        interaction_query = db.query(InteractionAnalysis.conversation_id).distinct()
        
        if min_csi is not None:
            interaction_query = interaction_query.filter(InteractionAnalysis.csi_score >= min_csi)
        if max_csi is not None:
            interaction_query = interaction_query.filter(InteractionAnalysis.csi_score <= max_csi)
        if start_date:
            interaction_query = interaction_query.filter(InteractionAnalysis.interaction_start >= start_date)
        if end_date:
            interaction_query = interaction_query.filter(InteractionAnalysis.interaction_end <= end_date)
        
        conversation_ids = [row[0] for row in interaction_query.all()]
        
        if not conversation_ids:
            # Return empty CSV
            df = pd.DataFrame()
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            return csv_buffer.getvalue()
        
        # Get messages from those conversations
        messages = db.query(Message).join(Conversation).filter(
            Message.conversation_id.in_(conversation_ids)
        ).order_by(Message.social_create_time).all()
        
        # Convert to pandas DataFrame
        data = []
        for message in messages:
            conversation = db.query(Conversation).filter(
                Conversation.id == message.conversation_id
            ).first()
            
            data.append({
                'message_id': message.id,
                'chat_id': conversation.fb_chat_id if conversation else None,
                'customer_name': conversation.customer_name if conversation else None,
                'timestamp': message.social_create_time,
                'direction': message.direction,
                'content': message.message_content,
                'sentiment_score': message.sentiment_score,
                'topics': ', '.join(message.topics) if message.topics else None,
                'agent_info': str(message.agent_info) if message.agent_info else None
            })
        
        df = pd.DataFrame(data)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error exporting interaction messages: {e}")
        raise