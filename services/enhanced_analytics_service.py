"""
Enhanced Analytics Service supporting both DailyAnalysis and InteractionAnalysis modes.
Maintains full backward compatibility while enabling interaction-based CSI calculation.
"""
import logging
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, case, or_
from datetime import datetime, date
import numpy as np

from models import Conversation, Metric, Message, DailyAnalysis, InteractionAnalysis
from schemas import CSIMetricsResponse, DailyMetricsResponse, HistoricalMetricsResponse
from services.interaction_service import InteractionService, InteractionSegment

logger = logging.getLogger(__name__)

# --- CSI Calculation Constants ---
CSI_PILLAR_WEIGHTS = {
    'effectiveness': 0.29,
    'effort': 0.27,
    'efficiency': 0.21,
    'empathy': 0.23,
}

class EnhancedAnalyticsService:
    """
    Enhanced analytics service supporting both daily and interaction-based analysis modes.
    """
    
    def __init__(self):
        self.interaction_service = InteractionService()
    
    # === CSI Score Calculation (Unified for both Daily and Interaction) ===
    
    def calculate_and_set_csi_score(self, analysis: Union[DailyAnalysis, InteractionAnalysis]):
        """
        Unified CSI calculation method for both DailyAnalysis and InteractionAnalysis.
        This function modifies the analysis object directly.
        """
        # Helper to safely calculate averages, returning None if all inputs are None
        def safe_avg(values: List[Optional[float]]) -> Optional[float]:
            valid_values = [v for v in values if v is not None]
            return np.mean(valid_values) if valid_values else None

        # 1. Calculate Pillar Scores from Micro-Metrics
        
        # Effectiveness
        analysis.effectiveness_score = safe_avg([
            analysis.resolution_achieved,
            analysis.fcr_score
        ])

        # Effort (invert CES score from 1-7 to 0-10)
        if analysis.ces is not None:
            analysis.effort_score = ((analysis.ces - 1) / 6) * 10

        # Efficiency (invert time-based scores and scale to 0-10)
        def scale_time(value, max_time): # Lower time = higher score
            if value is None or value < 0:  # Handle negative times
                return None
            # Cap the value at 3x max time to prevent extreme scores
            capped_value = min(value, max_time * 3.0)
            normalized = capped_value / max_time
            efficiency_score = max(0, (1 - normalized)) * 10
            # Ensure score is within 0-10 range
            return min(10.0, max(0.0, efficiency_score))

        efficiency_scores = [
            scale_time(analysis.first_response_time, 3600), # Max 1 hour
            scale_time(analysis.avg_response_time, 1800), # Max 30 mins
            scale_time(analysis.total_handling_time * 60 if analysis.total_handling_time is not None else None, 7200) # Max 2 hours
        ]
        analysis.efficiency_score = safe_avg(efficiency_scores)

        # Empathy
        analysis.empathy_score = safe_avg([
            analysis.sentiment_score,
            (analysis.sentiment_shift + 5) if analysis.sentiment_shift is not None else None # Normalize shift to 0-10
        ])

        # 2. Calculate the final CSI score
        pillar_scores = {
            'effectiveness': analysis.effectiveness_score,
            'effort': analysis.effort_score,
            'efficiency': analysis.efficiency_score,
            'empathy': analysis.empathy_score
        }

        # Handle missing pillar scores by using defaults or skipping calculation
        valid_pillars = {k: v for k, v in pillar_scores.items() if v is not None}
        
        if len(valid_pillars) < 3:  # Need at least 3 pillars for meaningful CSI
            analysis.csi_score = None
            return

        # Calculate weighted average using only valid pillars, adjusting weights proportionally
        total_weight = sum(CSI_PILLAR_WEIGHTS[p] for p in valid_pillars.keys())
        if total_weight == 0:
            analysis.csi_score = None
            return
            
        csi_score = sum(valid_pillars[p] * CSI_PILLAR_WEIGHTS[p] for p in valid_pillars) / total_weight
        
        # Ensure CSI score is within 0-10 range
        analysis.csi_score = round(min(10.0, max(0.0, csi_score)), 2)
    
    # === Interaction-Based Analysis Methods ===
    
    def detect_and_analyze_interactions(
        self, 
        messages: List[Dict[str, Any]], 
        conversation_id: int,
        db: Session
    ) -> List[InteractionAnalysis]:
        """
        Detect interactions within messages and create InteractionAnalysis objects.
        
        Args:
            messages: List of message dictionaries with required fields
            conversation_id: Database ID of the conversation
            db: Database session for lookups
            
        Returns:
            List of InteractionAnalysis objects (not yet saved to DB)
        """
        # Detect interaction boundaries
        interaction_segments = self.interaction_service.detect_interactions(messages)
        
        interaction_analyses = []
        
        for segment in interaction_segments:
            # Get messages for this interaction
            interaction_messages = [
                msg for msg in messages 
                if segment.start_message_id <= msg['id'] <= segment.end_message_id
            ]
            
            # Calculate metrics for this interaction
            interaction_analysis = self.create_interaction_analysis_from_messages(
                interaction_messages=interaction_messages,
                conversation_id=conversation_id,
                segment=segment
            )
            
            interaction_analyses.append(interaction_analysis)
            
        return interaction_analyses
    
    def create_interaction_analysis_from_messages(
        self,
        interaction_messages: List[Dict[str, Any]],
        conversation_id: int,
        segment: InteractionSegment
    ) -> InteractionAnalysis:
        """
        Create an InteractionAnalysis object from interaction messages and metadata.
        """
        # Calculate micro-metrics from messages
        metrics = self.calculate_interaction_metrics(interaction_messages)
        
        # Create InteractionAnalysis object
        interaction_analysis = InteractionAnalysis(
            conversation_id=conversation_id,
            start_message_id=segment.start_message_id,
            end_message_id=segment.end_message_id,
            interaction_start=segment.start_time,
            interaction_end=segment.end_time,
            interaction_type=segment.interaction_type,
            boundary_method=segment.boundary_method,
            boundary_confidence=segment.boundary_confidence,
            
            # Micro-metrics
            sentiment_score=metrics.get('sentiment_score'),
            sentiment_shift=metrics.get('sentiment_shift'),
            resolution_achieved=metrics.get('resolution_achieved'),
            fcr_score=metrics.get('fcr_score'),
            ces=metrics.get('ces'),
            common_topics=metrics.get('common_topics'),
            first_response_time=metrics.get('first_response_time'),
            avg_response_time=metrics.get('avg_response_time'),
            total_handling_time=metrics.get('total_handling_time'),
        )
        
        # Calculate and set CSI scores using unified method
        self.calculate_and_set_csi_score(interaction_analysis)
        
        return interaction_analysis
    
    def calculate_interaction_metrics(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate micro-metrics for an interaction from its messages.
        
        This is a simplified version - in production, this would use the same
        sophisticated analysis as the existing daily analysis system.
        """
        if not messages:
            return {}
        
        customer_messages = [msg for msg in messages if msg.get('direction') == 'to_company']
        agent_messages = [msg for msg in messages if msg.get('direction') == 'to_client']
        
        # Basic metrics calculation
        metrics = {}
        
        # Sentiment analysis (placeholder - would integrate with existing sentiment analysis)
        metrics['sentiment_score'] = 6.5  # Default neutral sentiment (0-10 scale)
        metrics['sentiment_shift'] = 0.0   # No shift detected (-5 to +5 scale)
        
        # Resolution detection (look for resolution keywords)
        resolution_keywords = ['resolved', 'fixed', 'working', 'restored', 'sorted', 'thanks']
        has_resolution = any(
            any(keyword in msg.get('message_content', '').lower() for keyword in resolution_keywords)
            for msg in customer_messages
        )
        metrics['resolution_achieved'] = 8.0 if has_resolution else 4.0  # 0-10 scale
        
        # First Contact Resolution (if interaction resolves in single exchange)
        metrics['fcr_score'] = 8.5 if has_resolution and len(agent_messages) == 1 else 5.5  # 0-10 scale
        
        # Customer Effort Score (based on interaction length) - 1-7 scale, lower is better
        interaction_length = len(customer_messages) + len(agent_messages)
        if interaction_length <= 3:
            metrics['ces'] = 2.0  # Low effort
        elif interaction_length <= 6:
            metrics['ces'] = 4.0  # Medium effort  
        else:
            metrics['ces'] = 6.0  # High effort
        
        # Topic extraction (simplified)
        content_text = ' '.join(msg.get('message_content', '') for msg in messages).lower()
        topics = []
        if 'power' in content_text or 'outage' in content_text or 'electricity' in content_text:
            topics.append('outage')
        if 'bill' in content_text or 'payment' in content_text or 'account' in content_text:
            topics.append('billing')
        if 'token' in content_text or 'prepaid' in content_text:
            topics.append('prepaid')
        metrics['common_topics'] = topics or ['general inquiry']
        
        # Timing metrics (if timestamps available)
        if len(messages) >= 2:
            start_time = messages[0].get('social_create_time')
            end_time = messages[-1].get('social_create_time')
            
            if start_time and end_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                
                total_duration = (end_time - start_time).total_seconds()
                # Cap total handling time at reasonable maximum (8 hours = 480 minutes)
                metrics['total_handling_time'] = min(total_duration / 60, 480)
                
                # First response time (time from first customer message to first agent response)
                first_customer = next((msg for msg in messages if msg.get('direction') == 'to_company'), None)
                first_agent = next((msg for msg in messages if msg.get('direction') == 'to_client'), None)
                
                if first_customer and first_agent:
                    customer_time = first_customer.get('social_create_time')
                    agent_time = first_agent.get('social_create_time')
                    
                    if isinstance(customer_time, str):
                        customer_time = datetime.fromisoformat(customer_time.replace('Z', '+00:00'))
                    if isinstance(agent_time, str):
                        agent_time = datetime.fromisoformat(agent_time.replace('Z', '+00:00'))
                    
                    response_time = (agent_time - customer_time).total_seconds()
                    metrics['first_response_time'] = max(0, response_time)
                    metrics['avg_response_time'] = response_time  # Simplified for single response
        
        return metrics
    
    # === Backward Compatibility Methods ===
    
    def calculate_and_set_daily_csi_score(self, daily_analysis: DailyAnalysis):
        """
        Legacy method for backward compatibility.
        Delegates to the unified CSI calculation method.
        """
        self.calculate_and_set_csi_score(daily_analysis)
    
    # === Query Methods Supporting Both Modes ===
    
    def get_historical_metrics(
        self, 
        db: Session, 
        start_date: date, 
        end_date: date,
        mode: str = 'daily'
    ) -> Dict[str, Any]:
        """
        Get historical metrics supporting both daily and interaction modes.
        
        Args:
            db: Database session
            start_date: Start date for analysis
            end_date: End date for analysis  
            mode: 'daily' or 'interaction' analysis mode
            
        Returns:
            Historical metrics aggregated by the specified mode
        """
        if mode == 'interaction':
            return self._get_interaction_historical_metrics(db, start_date, end_date)
        else:
            return self._get_daily_historical_metrics(db, start_date, end_date)
    
    def _get_daily_historical_metrics(self, db: Session, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get historical metrics from DailyAnalysis (existing functionality)."""
        results = db.query(
            DailyAnalysis.analysis_date.label("analysis_date"),
            func.count(func.distinct(DailyAnalysis.conversation_id)).label("total_conversations"),
            func.avg(DailyAnalysis.csi_score).label("avg_csi_score"),
            func.avg(DailyAnalysis.resolution_achieved).label("avg_resolution_achieved"),
            func.avg(DailyAnalysis.fcr_score).label("avg_fcr_score"),
            func.avg(DailyAnalysis.ces).label("avg_customer_effort_score"),
            func.avg(DailyAnalysis.effectiveness_score).label("avg_effectiveness_score"),
            func.avg(DailyAnalysis.efficiency_score).label("avg_efficiency_score"),
            func.avg(DailyAnalysis.effort_score).label("avg_effort_score"),
            func.avg(DailyAnalysis.empathy_score).label("avg_empathy_score")
        ).filter(DailyAnalysis.analysis_date.between(start_date, end_date))\
         .group_by(DailyAnalysis.analysis_date)\
         .order_by(DailyAnalysis.analysis_date).all()
        
        return {
            'mode': 'daily',
            'data': [dict(row._mapping) for row in results]
        }
    
    def _get_interaction_historical_metrics(self, db: Session, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get historical metrics from InteractionAnalysis (new functionality)."""
        results = db.query(
            func.date(InteractionAnalysis.interaction_start).label("analysis_date"),
            func.count(func.distinct(InteractionAnalysis.conversation_id)).label("total_conversations"),
            func.count(InteractionAnalysis.id).label("total_interactions"),
            func.avg(InteractionAnalysis.csi_score).label("avg_csi_score"),
            func.avg(InteractionAnalysis.resolution_achieved).label("avg_resolution_achieved"),
            func.avg(InteractionAnalysis.fcr_score).label("avg_fcr_score"),
            func.avg(InteractionAnalysis.ces).label("avg_customer_effort_score"),
            func.avg(InteractionAnalysis.effectiveness_score).label("avg_effectiveness_score"),
            func.avg(InteractionAnalysis.efficiency_score).label("avg_efficiency_score"),
            func.avg(InteractionAnalysis.effort_score).label("avg_effort_score"),
            func.avg(InteractionAnalysis.empathy_score).label("avg_empathy_score")
        ).filter(
            func.date(InteractionAnalysis.interaction_start).between(start_date, end_date)
        ).group_by(func.date(InteractionAnalysis.interaction_start))\
         .order_by(func.date(InteractionAnalysis.interaction_start)).all()
        
        return {
            'mode': 'interaction',
            'data': [dict(row._mapping) for row in results]
        }

    def get_conversations_with_interaction_summary(
        self, 
        db: Session,
        min_csi: Optional[float] = None,
        max_csi: Optional[float] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation summaries with interaction-based aggregations for export.
        """
        try:
            # Build query with filters
            query = db.query(
                Conversation.fb_chat_id,
                Conversation.customer_name,
                Conversation.created_at,
                Conversation.total_messages,
                Conversation.customer_messages,
                Conversation.agent_messages,
                Conversation.first_message_time,
                Conversation.last_message_time,
                func.avg(InteractionAnalysis.csi_score).label("avg_csi"),
                func.avg(InteractionAnalysis.effectiveness_score).label("avg_effectiveness"),
                func.avg(InteractionAnalysis.efficiency_score).label("avg_efficiency"),
                func.avg(InteractionAnalysis.effort_score).label("avg_effort"),
                func.avg(InteractionAnalysis.empathy_score).label("avg_empathy"),
                func.count(InteractionAnalysis.id).label("interaction_count"),
                func.avg(InteractionAnalysis.interaction_duration).label("avg_duration")
            ).join(InteractionAnalysis, Conversation.id == InteractionAnalysis.conversation_id)
            
            # Apply filters
            if min_csi is not None:
                query = query.filter(InteractionAnalysis.csi_score >= min_csi)
            if max_csi is not None:
                query = query.filter(InteractionAnalysis.csi_score <= max_csi)
            if start_date:
                query = query.filter(InteractionAnalysis.interaction_start >= start_date)
            if end_date:
                query = query.filter(InteractionAnalysis.interaction_end <= end_date)
            
            # Group by conversation
            query = query.group_by(
                Conversation.id,
                Conversation.fb_chat_id,
                Conversation.customer_name,
                Conversation.created_at,
                Conversation.total_messages,
                Conversation.customer_messages,
                Conversation.agent_messages,
                Conversation.first_message_time,
                Conversation.last_message_time
            )
            
            results = query.all()
            
            # Convert to list of dictionaries
            data = []
            for row in results:
                data.append({
                    'chat_id': row.fb_chat_id,
                    'customer_name': row.customer_name,
                    'created_at': row.created_at,
                    'total_messages': row.total_messages,
                    'customer_messages': row.customer_messages,
                    'agent_messages': row.agent_messages,
                    'first_message_time': row.first_message_time,
                    'last_message_time': row.last_message_time,
                    'avg_csi_score': round(row.avg_csi, 2) if row.avg_csi else None,
                    'avg_effectiveness_score': round(row.avg_effectiveness, 2) if row.avg_effectiveness else None,
                    'avg_efficiency_score': round(row.avg_efficiency, 2) if row.avg_efficiency else None,
                    'avg_effort_score': round(row.avg_effort, 2) if row.avg_effort else None,
                    'avg_empathy_score': round(row.avg_empathy, 2) if row.avg_empathy else None,
                    'interaction_count': row.interaction_count,
                    'avg_interaction_duration_minutes': round(row.avg_duration, 2) if row.avg_duration else None
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting conversations with interaction summary: {e}")
            raise

    def get_interaction_details(self, db: Session, interaction_id: int) -> Dict[str, Any]:
        """Get detailed information for a specific interaction."""
        try:
            interaction = db.query(InteractionAnalysis).filter(
                InteractionAnalysis.id == interaction_id
            ).first()
            
            if not interaction:
                raise ValueError(f"Interaction {interaction_id} not found")
            
            # Get conversation info
            conversation = db.query(Conversation).filter(
                Conversation.id == interaction.conversation_id
            ).first()
            
            # Get messages within interaction timeframe
            messages = db.query(Message).filter(
                Message.conversation_id == interaction.conversation_id,
                Message.social_create_time >= interaction.interaction_start,
                Message.social_create_time <= interaction.interaction_end
            ).order_by(Message.social_create_time).all()
            
            return {
                "interaction": {
                    "id": interaction.id,
                    "conversation_id": interaction.conversation_id,
                    "chat_id": conversation.fb_chat_id if conversation else None,
                    "customer_name": conversation.customer_name if conversation else None,
                    "interaction_start": interaction.interaction_start,
                    "interaction_end": interaction.interaction_end,
                    "interaction_duration": interaction.interaction_duration,
                    "interaction_type": interaction.interaction_type,
                    "interaction_complexity": interaction.interaction_complexity,
                    "message_count": interaction.message_count,
                    "turns_count": interaction.turns_count,
                    "csi_score": interaction.csi_score,
                    "effectiveness_score": interaction.effectiveness_score,
                    "efficiency_score": interaction.efficiency_score,
                    "effort_score": interaction.effort_score,
                    "empathy_score": interaction.empathy_score,
                    "sentiment_score": interaction.sentiment_score,
                    "sentiment_shift": interaction.sentiment_shift,
                    "resolution_achieved": interaction.resolution_achieved,
                    "fcr_score": interaction.fcr_score,
                    "ces": interaction.ces,
                    "first_response_time": interaction.first_response_time,
                    "avg_response_time": interaction.avg_response_time,
                    "total_handling_time": interaction.total_handling_time,
                    "common_topics": interaction.common_topics,
                    "created_at": interaction.created_at
                },
                "messages": [
                    {
                        "id": msg.id,
                        "timestamp": msg.social_create_time,
                        "direction": msg.direction,
                        "content": msg.message_content,
                        "sentiment_score": msg.sentiment_score,
                        "topics": msg.topics,
                        "agent_info": msg.agent_info
                    }
                    for msg in messages
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting interaction {interaction_id} details: {e}")
            raise

    async def get_sentiment_trend(
        self, 
        db: Session, 
        start_date: date, 
        end_date: date, 
        mode: str = "daily"
    ) -> Dict[str, Any]:
        """Get sentiment trend data for charts."""
        try:
            if mode == "interaction":
                results = db.query(
                    func.date(InteractionAnalysis.interaction_start).label("date"),
                    func.avg(InteractionAnalysis.sentiment_score).label("avg_sentiment"),
                    func.count(InteractionAnalysis.id).label("interaction_count")
                ).filter(
                    func.date(InteractionAnalysis.interaction_start).between(start_date, end_date),
                    InteractionAnalysis.sentiment_score.isnot(None)
                ).group_by(func.date(InteractionAnalysis.interaction_start))\
                 .order_by(func.date(InteractionAnalysis.interaction_start)).all()
                
                return {
                    "sentiment_trend": [
                        {
                            "date": str(row.date),
                            "avg_sentiment": round(row.avg_sentiment, 2) if row.avg_sentiment else 0,
                            "sample_count": row.interaction_count
                        }
                        for row in results
                    ],
                    "mode": "interaction",
                    "date_range": {"start_date": start_date, "end_date": end_date}
                }
            else:
                # Daily mode - delegate to existing analytics service if available
                results = db.query(
                    func.date(DailyAnalysis.analysis_date).label("date"),
                    func.avg(DailyAnalysis.sentiment_score).label("avg_sentiment"),
                    func.count(DailyAnalysis.id).label("analysis_count")
                ).filter(
                    DailyAnalysis.analysis_date.between(start_date, end_date),
                    DailyAnalysis.sentiment_score.isnot(None)
                ).group_by(func.date(DailyAnalysis.analysis_date))\
                 .order_by(func.date(DailyAnalysis.analysis_date)).all()
                
                return {
                    "sentiment_trend": [
                        {
                            "date": str(row.date),
                            "avg_sentiment": round(row.avg_sentiment, 2) if row.avg_sentiment else 0,
                            "sample_count": row.analysis_count
                        }
                        for row in results
                    ],
                    "mode": "daily",
                    "date_range": {"start_date": start_date, "end_date": end_date}
                }
                
        except Exception as e:
            logger.error(f"Error getting sentiment trend ({mode}): {e}")
            raise

    async def get_csi_trend(
        self, 
        db: Session, 
        start_date: date, 
        end_date: date, 
        mode: str = "daily"
    ) -> Dict[str, Any]:
        """Get CSI and pillar trend data for charts."""
        try:
            if mode == "interaction":
                results = db.query(
                    func.date(InteractionAnalysis.interaction_start).label("date"),
                    func.avg(InteractionAnalysis.csi_score).label("avg_csi"),
                    func.avg(InteractionAnalysis.effectiveness_score).label("avg_effectiveness"),
                    func.avg(InteractionAnalysis.efficiency_score).label("avg_efficiency"),
                    func.avg(InteractionAnalysis.effort_score).label("avg_effort"),
                    func.avg(InteractionAnalysis.empathy_score).label("avg_empathy"),
                    func.count(InteractionAnalysis.id).label("interaction_count")
                ).filter(
                    func.date(InteractionAnalysis.interaction_start).between(start_date, end_date),
                    InteractionAnalysis.csi_score.isnot(None)
                ).group_by(func.date(InteractionAnalysis.interaction_start))\
                 .order_by(func.date(InteractionAnalysis.interaction_start)).all()
                
                return {
                    "csi_trend": [
                        {
                            "date": str(row.date),
                            "avg_csi_score": round(row.avg_csi, 2) if row.avg_csi else 0,
                            "avg_effectiveness_score": round(row.avg_effectiveness, 2) if row.avg_effectiveness else 0,
                            "avg_efficiency_score": round(row.avg_efficiency, 2) if row.avg_efficiency else 0,
                            "avg_effort_score": round(row.avg_effort, 2) if row.avg_effort else 0,
                            "avg_empathy_score": round(row.avg_empathy, 2) if row.avg_empathy else 0,
                            "sample_count": row.interaction_count
                        }
                        for row in results
                    ],
                    "mode": "interaction",
                    "date_range": {"start_date": start_date, "end_date": end_date}
                }
            else:
                # Daily mode
                results = db.query(
                    DailyAnalysis.analysis_date.label("date"),
                    func.avg(DailyAnalysis.csi_score).label("avg_csi"),
                    func.avg(DailyAnalysis.effectiveness_score).label("avg_effectiveness"),
                    func.avg(DailyAnalysis.efficiency_score).label("avg_efficiency"),
                    func.avg(DailyAnalysis.effort_score).label("avg_effort"),
                    func.avg(DailyAnalysis.empathy_score).label("avg_empathy"),
                    func.count(DailyAnalysis.id).label("analysis_count")
                ).filter(
                    DailyAnalysis.analysis_date.between(start_date, end_date),
                    DailyAnalysis.csi_score.isnot(None)
                ).group_by(DailyAnalysis.analysis_date)\
                 .order_by(DailyAnalysis.analysis_date).all()
                
                return {
                    "csi_trend": [
                        {
                            "date": str(row.date),
                            "avg_csi_score": round(row.avg_csi, 2) if row.avg_csi else 0,
                            "avg_effectiveness_score": round(row.avg_effectiveness, 2) if row.avg_effectiveness else 0,
                            "avg_efficiency_score": round(row.avg_efficiency, 2) if row.avg_efficiency else 0,
                            "avg_effort_score": round(row.avg_effort, 2) if row.avg_effort else 0,
                            "avg_empathy_score": round(row.avg_empathy, 2) if row.avg_empathy else 0,
                            "sample_count": row.analysis_count
                        }
                        for row in results
                    ],
                    "mode": "daily",
                    "date_range": {"start_date": start_date, "end_date": end_date}
                }
                
        except Exception as e:
            logger.error(f"Error getting CSI trend ({mode}): {e}")
            raise

    def get_cached_csi_metrics(self, db: Session, mode: str = "daily") -> Dict[str, Any]:
        """
        Get cached CSI metrics, compatible with existing analytics service interface.
        """
        if mode == "interaction":
            # For interaction mode, calculate fresh metrics since we don't have caching yet
            return self.calculate_and_cache_csi_metrics(db, mode="interaction")
        else:
            # Delegate to existing analytics service for daily mode
            from services.analytics_service import analytics_service
            return analytics_service.get_cached_csi_metrics(db)
    
    def calculate_and_cache_csi_metrics(self, db: Session, mode: str = "daily") -> Dict[str, Any]:
        """
        Calculate and cache CSI metrics, compatible with existing analytics service interface.
        """
        if mode == "interaction":
            # Calculate interaction-based metrics
            interactions = db.query(InteractionAnalysis).filter(
                InteractionAnalysis.csi_score.isnot(None)
            ).all()
            
            if not interactions:
                # Return default structure if no data
                return {
                    "csi": 0.0,
                    "resolution_quality": 0.0,
                    "service_timeliness": 0.0, 
                    "customer_ease": 0.0,
                    "interaction_quality": 0.0,
                    "sentiment_score": 0.0,
                    "sentiment_shift": 0.0,
                    "resolution_achieved": 0.0,
                    "fcr_score": 0.0,
                    "ces": 0.0,
                    "first_response_time": 0.0,
                    "avg_response_time": 0.0,
                    "total_handling_time": 0.0,
                    "avg_interaction_duration": 0.0,
                    "avg_message_count": 0.0,
                    "avg_turns_count": 0.0,
                    "sample_count": 0,
                    "interaction_count": 0,
                    "pillar_weights": CSI_PILLAR_WEIGHTS,
                    "interaction_complexity_distribution": {}
                }
            
            # Calculate averages
            def safe_avg(values):
                filtered = [v for v in values if v is not None]
                return np.mean(filtered) if filtered else 0.0
            
            csi_scores = [i.csi_score for i in interactions if i.csi_score is not None]
            avg_csi = safe_avg(csi_scores)
            
            return {
                "csi": avg_csi * 10,  # Convert to 0-100 scale
                "resolution_quality": safe_avg([i.effectiveness_score for i in interactions]) * 10,
                "service_timeliness": safe_avg([i.efficiency_score for i in interactions]) * 10,
                "customer_ease": safe_avg([i.effort_score for i in interactions]) * 10,
                "interaction_quality": safe_avg([i.empathy_score for i in interactions]) * 10,
                "sentiment_score": safe_avg([i.sentiment_score for i in interactions]),
                "sentiment_shift": safe_avg([i.sentiment_shift for i in interactions]),
                "resolution_achieved": safe_avg([i.resolution_achieved for i in interactions]),
                "fcr_score": safe_avg([i.fcr_score for i in interactions]),
                "ces": safe_avg([i.ces for i in interactions]),
                "first_response_time": safe_avg([i.first_response_time for i in interactions]),
                "avg_response_time": safe_avg([i.avg_response_time for i in interactions]),
                "total_handling_time": safe_avg([i.total_handling_time for i in interactions]),
                "avg_interaction_duration": safe_avg([i.interaction_duration for i in interactions]),
                "avg_message_count": safe_avg([i.message_count for i in interactions]),
                "avg_turns_count": safe_avg([i.turns_count for i in interactions]),
                "sample_count": len(interactions),
                "interaction_count": len(interactions),
                "pillar_weights": CSI_PILLAR_WEIGHTS,
                "interaction_complexity_distribution": self._get_complexity_distribution(interactions)
            }
        else:
            # Delegate to existing analytics service for daily mode
            from services.analytics_service import analytics_service
            return analytics_service.calculate_and_cache_csi_metrics(db)
    
    def _get_complexity_distribution(self, interactions: List[InteractionAnalysis]) -> Dict[str, int]:
        """Get distribution of interaction complexities."""
        distribution = {}
        for interaction in interactions:
            if interaction.interaction_complexity:
                complexity = interaction.interaction_complexity
                distribution[complexity] = distribution.get(complexity, 0) + 1
        return distribution
    
    def get_interaction_details(self, db: Session, interaction_id: int) -> Dict[str, Any]:
        """Get detailed information for a specific interaction."""
        interaction = db.query(InteractionAnalysis).filter(
            InteractionAnalysis.id == interaction_id
        ).first()
        
        if not interaction:
            raise ValueError(f"Interaction {interaction_id} not found")
        
        conversation = db.query(Conversation).filter(
            Conversation.id == interaction.conversation_id
        ).first()
        
        return {
            "interaction": interaction,
            "conversation": conversation,
            "chat_id": conversation.fb_chat_id if conversation else None,
            "customer_name": conversation.customer_name if conversation else None
        }
    
    async def get_sentiment_trend(self, db: Session, start_date: date, end_date: date, mode: str = "daily") -> Dict[str, Any]:
        """Get sentiment trend data for charts."""
        if mode == "interaction":
            # Get daily sentiment averages from interactions
            results = db.query(
                func.date(InteractionAnalysis.interaction_start).label("date"),
                func.avg(InteractionAnalysis.sentiment_score).label("avg_sentiment"),
                func.count(InteractionAnalysis.id).label("interaction_count")
            ).filter(
                func.date(InteractionAnalysis.interaction_start).between(start_date, end_date),
                InteractionAnalysis.sentiment_score.isnot(None)
            ).group_by(func.date(InteractionAnalysis.interaction_start))\
             .order_by(func.date(InteractionAnalysis.interaction_start)).all()
            
            return {
                "sentiment_trend": [
                    {
                        "date": str(row.date),
                        "avg_sentiment": round(row.avg_sentiment, 3) if row.avg_sentiment else 0,
                        "sample_count": row.interaction_count
                    }
                    for row in results
                ]
            }
        else:
            # Delegate to existing analytics service
            from services.analytics_service import analytics_service
            return await analytics_service.get_sentiment_trend(db, start_date, end_date)
    
    async def get_csi_trend(self, db: Session, start_date: date, end_date: date, mode: str = "daily") -> Dict[str, Any]:
        """Get CSI trend data for charts."""
        if mode == "interaction":
            # Get daily CSI averages from interactions
            results = db.query(
                func.date(InteractionAnalysis.interaction_start).label("date"),
                func.avg(InteractionAnalysis.csi_score).label("avg_csi"),
                func.avg(InteractionAnalysis.effectiveness_score).label("avg_effectiveness"),
                func.avg(InteractionAnalysis.efficiency_score).label("avg_efficiency"),
                func.avg(InteractionAnalysis.effort_score).label("avg_effort"),
                func.avg(InteractionAnalysis.empathy_score).label("avg_empathy"),
                func.count(InteractionAnalysis.id).label("interaction_count")
            ).filter(
                func.date(InteractionAnalysis.interaction_start).between(start_date, end_date),
                InteractionAnalysis.csi_score.isnot(None)
            ).group_by(func.date(InteractionAnalysis.interaction_start))\
             .order_by(func.date(InteractionAnalysis.interaction_start)).all()
            
            return {
                "csi_trend": [
                    {
                        "date": str(row.date),
                        "csi_score": round(row.avg_csi * 10, 2) if row.avg_csi else 0,  # Scale to 0-100
                        "effectiveness_score": round(row.avg_effectiveness * 10, 2) if row.avg_effectiveness else 0,
                        "efficiency_score": round(row.avg_efficiency * 10, 2) if row.avg_efficiency else 0,
                        "effort_score": round(row.avg_effort * 10, 2) if row.avg_effort else 0,
                        "empathy_score": round(row.avg_empathy * 10, 2) if row.avg_empathy else 0,
                        "sample_count": row.interaction_count
                    }
                    for row in results
                ]
            }
        else:
            # Delegate to existing analytics service
            from services.analytics_service import analytics_service
            return await analytics_service.get_csi_trend(db, start_date, end_date)

# Create service instance
enhanced_analytics_service = EnhancedAnalyticsService()

# Backward compatibility alias
def calculate_and_set_daily_csi_score(daily_analysis: DailyAnalysis):
    """Legacy function for backward compatibility."""
    enhanced_analytics_service.calculate_and_set_daily_csi_score(daily_analysis)