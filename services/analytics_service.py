"""
Service for calculating and caching all analytics, focusing on the new, expanded
Customer Satisfaction Index (CSI) model, calculated on a daily basis.
"""
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, tuple_, case, or_
from datetime import datetime, date
import numpy as np

from models import Conversation, Metric, Message, DailyAnalysis
from schemas import CSIMetricsResponse, DailyMetricsResponse, HistoricalMetricsResponse, PaginatedDailyAnalysisResponse, DailyAnalysisResponse

logger = logging.getLogger(__name__)

# --- CSI Calculation Constants from gemini-refactor.md ---
CSI_PILLAR_WEIGHTS = {
    'effectiveness': 0.29,
    'effort': 0.27,
    'efficiency': 0.21,
    'empathy': 0.23,
}

def calculate_and_set_daily_csi_score(daily_analysis: DailyAnalysis):
    """
    Calculates pillar scores from micro-metrics, then calculates the final 
    CSI score for a single DailyAnalysis object.
    This function modifies the daily_analysis object directly.
    """
    # Helper to safely calculate averages, returning None if all inputs are None
    def safe_avg(values: List[Optional[float]]) -> Optional[float]:
        valid_values = [v for v in values if v is not None]
        return np.mean(valid_values) if valid_values else None

    # 1. Calculate Pillar Scores from Micro-Metrics
    
    # Effectiveness
    daily_analysis.effectiveness_score = safe_avg([
        daily_analysis.resolution_achieved,
        daily_analysis.fcr_score
    ])

    # Effort (invert CES score from 1-7 to 0-10)
    if daily_analysis.ces is not None:
        daily_analysis.effort_score = ((7 - daily_analysis.ces) / 6) * 10

    # Efficiency (invert time-based scores and scale to 0-10)
    # Note: This is a simplified scaling. A more sophisticated approach might use logarithmic scaling.
    def scale_time(value, max_time): # Lower time = higher score
        return max(0, (1 - (value / max_time))) * 10 if value is not None else None

    efficiency_scores = [
        scale_time(daily_analysis.first_response_time, 3600), # Max 1 hour
        scale_time(daily_analysis.avg_response_time, 1800), # Max 30 mins
        scale_time(daily_analysis.total_handling_time * 60 if daily_analysis.total_handling_time is not None else None, 7200) # Max 2 hours (converted to secs)
    ]
    daily_analysis.efficiency_score = safe_avg(efficiency_scores)

    # Empathy
    daily_analysis.empathy_score = safe_avg([
        daily_analysis.sentiment_score,
        (daily_analysis.sentiment_shift + 5) if daily_analysis.sentiment_shift is not None else None # Normalize shift to 0-10
    ])

    # 2. Calculate the final CSI score for the day
    pillar_scores = {
        'effectiveness': daily_analysis.effectiveness_score,
        'effort': daily_analysis.effort_score,
        'efficiency': daily_analysis.efficiency_score,
        'empathy': daily_analysis.empathy_score
    }

    if not all(score is not None for score in pillar_scores.values()):
        daily_analysis.csi_score = None
        return

    csi_score = sum(pillar_scores[p] * CSI_PILLAR_WEIGHTS[p] for p in CSI_PILLAR_WEIGHTS)
    daily_analysis.csi_score = round(csi_score, 2)

class AnalyticsService:
    
    def get_historical_csi_metrics(self, db: Session, start_date: date, end_date: date) -> HistoricalMetricsResponse:
        """
        Calculates daily average CSI and micro/macro metrics for a given date range
        from the DailyAnalysis table.
        """
        try:
            results = db.query(
                DailyAnalysis.analysis_date.label("message_timestamp"),
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
            .order_by(DailyAnalysis.analysis_date)\
            .all()

            daily_metrics = [DailyMetricsResponse(**row._asdict()) for row in results]
            return HistoricalMetricsResponse(data=daily_metrics)

        except Exception as e:
            logger.error(f"Error calculating historical CSI metrics: {e}", exc_info=True)
            raise

    def calculate_and_cache_csi_metrics(self, db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Calculate all frontend-facing metrics from DailyAnalysis and cache them.
        This is the primary engine for the GET /api/metrics endpoint.
        """
        try:
            # Base query for the current period
            query = db.query(DailyAnalysis).filter(DailyAnalysis.csi_score.isnot(None))
            if start_date and end_date:
                query = query.filter(DailyAnalysis.analysis_date.between(start_date, end_date))

            # --- Calculate Current Period Metrics ---
            total_analyzed = query.count()
            if total_analyzed == 0:
                return self._get_empty_frontend_metrics()

            # Calculate averages for each pillar and the overall CSI score
            avg_effectiveness = query.with_entities(func.avg(DailyAnalysis.effectiveness_score)).scalar() or 0.0
            avg_efficiency = query.with_entities(func.avg(DailyAnalysis.efficiency_score)).scalar() or 0.0
            avg_effort = query.with_entities(func.avg(DailyAnalysis.effort_score)).scalar() or 0.0
            avg_empathy = query.with_entities(func.avg(DailyAnalysis.empathy_score)).scalar() or 0.0
            overall_csi = query.with_entities(func.avg(DailyAnalysis.csi_score)).scalar() or 0.0
            
            # Calculate all micro-metrics averages
            avg_sentiment_score = query.with_entities(func.avg(DailyAnalysis.sentiment_score)).scalar() or 0.0
            avg_sentiment_shift = query.with_entities(func.avg(DailyAnalysis.sentiment_shift)).scalar() or 0.0
            avg_resolution_achieved = query.with_entities(func.avg(DailyAnalysis.resolution_achieved)).scalar() or 0.0
            avg_fcr_score = query.with_entities(func.avg(DailyAnalysis.fcr_score)).scalar() or 0.0
            avg_ces = query.with_entities(func.avg(DailyAnalysis.ces)).scalar() or 0.0
            avg_first_response_time = query.with_entities(func.avg(DailyAnalysis.first_response_time)).scalar() or 0.0
            avg_response_time = query.with_entities(func.avg(DailyAnalysis.avg_response_time)).scalar() or 0.0
            avg_total_handling_time = query.with_entities(func.avg(DailyAnalysis.total_handling_time)).scalar() or 0.0

            current_metrics = {
                "csi": overall_csi * 10,
                "resolution_quality": avg_effectiveness * 10,
                "service_timeliness": avg_efficiency * 10,
                "customer_ease": avg_effort * 10,
                "interaction_quality": avg_empathy * 10,
                
                # All micro-metrics
                "sentiment_score": avg_sentiment_score,
                "sentiment_shift": avg_sentiment_shift,
                "resolution_achieved": avg_resolution_achieved,
                "fcr_score": avg_fcr_score,
                "ces": avg_ces,
                "first_response_time": avg_first_response_time,
                "avg_response_time": avg_response_time,
                "total_handling_time": avg_total_handling_time,
                
                "sample_count": db.query(func.count(func.distinct(DailyAnalysis.conversation_id))).filter(DailyAnalysis.csi_score.isnot(None)).scalar(),
            }

            # --- Calculate Deltas (if applicable) ---
            # TODO: Implement delta calculation logic by querying the previous period

            current_metrics["deltas"] = None # Placeholder
            current_metrics["pillar_weights"] = CSI_PILLAR_WEIGHTS

            return current_metrics
            
        except Exception as e:
            logger.error(f"Error calculating frontend metrics: {e}", exc_info=True)
            raise

    def get_cached_csi_metrics(self, db: Session) -> CSIMetricsResponse:
        # This function will now be a simple wrapper around the main calculation
        # Caching logic can be re-introduced here if performance becomes an issue
        metrics = self.calculate_and_cache_csi_metrics(db)
        return CSIMetricsResponse(**metrics)

    def _get_empty_frontend_metrics(self) -> Dict[str, Any]:
        """Returns a dictionary with empty/zero values for the frontend metrics contract."""
        return {
            'csi': 0.0, 'resolution_quality': 0.0, 'service_timeliness': 0.0,
            'customer_ease': 0.0, 'interaction_quality': 0.0, 'sample_count': 0,
            
            # All micro-metrics
            'sentiment_score': 0.0, 'sentiment_shift': 0.0, 'resolution_achieved': 0.0,
            'fcr_score': 0.0, 'ces': 0.0, 'first_response_time': 0.0,
            'avg_response_time': 0.0, 'total_handling_time': 0.0,
            
            'deltas': None, 'pillar_weights': CSI_PILLAR_WEIGHTS
        }

    async def get_sentiment_trend(self, db: Session, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Calculates daily average sentiment for a given date range, formatted for charts.
        """
        try:
            results = db.query(
                DailyAnalysis.analysis_date,
                func.avg(DailyAnalysis.sentiment_score)
            ).filter(DailyAnalysis.analysis_date.between(start_date, end_date))\
            .group_by(DailyAnalysis.analysis_date)\
            .order_by(DailyAnalysis.analysis_date)\
            .all()

            return [{"date": row[0].strftime("%Y-%m-%d"), "sentiment": row[1]} for row in results]

        except Exception as e:
            logger.error(f"Error calculating sentiment trend: {e}", exc_info=True)
            raise

    async def get_csi_trend(self, db: Session, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Calculates daily average CSI and all pillar scores for a given date range, formatted for charts.
        """
        try:
            results = db.query(
                DailyAnalysis.analysis_date,
                func.avg(DailyAnalysis.csi_score).label("csi_score"),
                func.avg(DailyAnalysis.effectiveness_score).label("effectiveness_score"),
                func.avg(DailyAnalysis.effort_score).label("effort_score"),
                func.avg(DailyAnalysis.efficiency_score).label("efficiency_score"),
                func.avg(DailyAnalysis.empathy_score).label("empathy_score")
            ).filter(DailyAnalysis.analysis_date.between(start_date, end_date))\
            .group_by(DailyAnalysis.analysis_date)\
            .order_by(DailyAnalysis.analysis_date)\
            .all()

            return [
                {
                    "date": row.analysis_date.strftime("%Y-%m-%d"),
                    "csi_score": row.csi_score,
                    "effectiveness_score": row.effectiveness_score,
                    "effort_score": row.effort_score,
                    "efficiency_score": row.efficiency_score,
                    "empathy_score": row.empathy_score,
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Error calculating CSI trend: {e}", exc_info=True)
            raise

    def get_daily_analyses_with_details(self, db: Session, start_date: date, end_date: date, page: int, page_size: int) -> PaginatedDailyAnalysisResponse:
        """
        Fetches a paginated list of daily analyses with details for the explorer.
        """
        offset = (page - 1) * page_size
        
        query = db.query(DailyAnalysis).options(
            joinedload(DailyAnalysis.conversation)
        ).filter(
            DailyAnalysis.analysis_date.between(start_date, end_date),
            DailyAnalysis.csi_score.isnot(None)
        )
        
        total_items = query.count()
        total_pages = (total_items + page_size - 1) // page_size
        
        results = query.order_by(DailyAnalysis.analysis_date.desc()).limit(page_size).offset(offset).all()

        if page == 1:
            query = query.filter(
            DailyAnalysis.effectiveness_score.isnot(None),
            DailyAnalysis.effectiveness_score != 0,
            DailyAnalysis.effort_score.isnot(None),
            DailyAnalysis.effort_score != 0,
            DailyAnalysis.efficiency_score.isnot(None),
            DailyAnalysis.efficiency_score != 0,
            DailyAnalysis.empathy_score.isnot(None),
            DailyAnalysis.empathy_score != 0,
            DailyAnalysis.total_handling_time.isnot(None),
            DailyAnalysis.total_handling_time != 0
            )
            
            # Re-execute query for page 1 with workaround filters/ordering
            results = query.limit(page_size).offset(offset).all()
        # --- END URGENT WORKAROUND ---

        # Efficiently fetch message counts for all analyses on the current page
        message_counts_map = {}
        if results:
            # Create a list of composite keys to filter messages
            conv_date_pairs = list(set([(res.conversation_id, res.analysis_date) for res in results]))

            # Build a list of AND conditions for each (conversation_id, date) pair
            conditions = []
            for convo_id, analysis_date in conv_date_pairs:
                conditions.append(
                    and_(
                        Message.conversation_id == convo_id,
                        func.date(Message.social_create_time) == analysis_date
                    )
                )
            
            if conditions:
                message_counts_query = db.query(
                    Message.conversation_id,
                    func.date(Message.social_create_time).label('analysis_date_group'),
                    func.count(Message.id).label('total_messages'),
                    func.sum(case((Message.direction == 'to_company', 1), else_=0)).label('customer_messages'),
                    func.sum(case((Message.direction == 'to_client', 1), else_=0)).label('agent_messages')
                ).filter(or_(*conditions)).group_by(
                    Message.conversation_id, 'analysis_date_group'
                )
                
                message_counts_map = {
                    (row.conversation_id, row.analysis_date_group): row for row in message_counts_query.all()
                }

        response_data = []
        for analysis in results:
            conversation_duration = None
            if analysis.conversation and analysis.conversation.last_message_time and analysis.conversation.first_message_time:
                conversation_duration = (analysis.conversation.last_message_time - analysis.conversation.first_message_time).total_seconds()

            # Query for daily active agents
            agents_list = []
            if analysis.conversation:
                agents_query = db.query(Message.agent_info).filter(
                    Message.conversation_id == analysis.conversation_id,
                    func.date(Message.social_create_time) == analysis.analysis_date,
                    Message.direction == 'to_client',
                    Message.agent_info.isnot(None)
                ).distinct().all()
                agents_list = [info[0] for info in agents_query if info[0] and (info[0].get('name') or info[0].get('email'))]
            
            # Get message counts from the pre-fetched map
            counts = message_counts_map.get((analysis.conversation_id, analysis.analysis_date))

            response_data.append({
                "daily_analysis_id": analysis.id,
                "conversation_id": analysis.conversation.fb_chat_id if analysis.conversation else None,
                "customer_name": analysis.conversation.customer_name if analysis.conversation else None,
                "analysis_date": analysis.analysis_date,
                "csi_score": analysis.csi_score,
                "effectiveness_score": analysis.effectiveness_score,
                "efficiency_score": analysis.efficiency_score,
                "effort_score": analysis.effort_score,
                "empathy_score": analysis.empathy_score,
                "common_topics": analysis.common_topics,
                "agents": agents_list,
                "conversation_duration": conversation_duration,
                "sentiment_score": analysis.sentiment_score,
                "sentiment_shift": analysis.sentiment_shift,
                "resolution_achieved": analysis.resolution_achieved,
                "fcr_score": analysis.fcr_score,
                "ces": analysis.ces,
                "first_response_time": analysis.first_response_time,
                "avg_response_time": analysis.avg_response_time,
                "total_handling_time": analysis.total_handling_time,
                # "total_messages": counts.total_messages if counts else 0,
                "customer_messages": counts.customer_messages if counts else 0,
                "agent_messages": counts.agent_messages if counts else 0
            })

        return PaginatedDailyAnalysisResponse(
            pagination={"page": page, "page_size": page_size, "total_items": total_items, "total_pages": total_pages},
            data=response_data
        )

    def get_transcript_for_daily_analysis(self, db: Session, daily_analysis_id: int) -> List[Message]:
        """
        Fetches all messages associated with a specific daily analysis, ordered by time.
        """
        analysis = db.query(DailyAnalysis).options(
            joinedload(DailyAnalysis.conversation).joinedload(Conversation.messages)
        ).filter(DailyAnalysis.id == daily_analysis_id).first()

        if not analysis:
            return []

        # Filter messages to only those on the specific analysis date
        daily_messages = [
            msg for msg in analysis.conversation.messages 
            if msg.social_create_time.date() == analysis.analysis_date.date()
        ]
        
        return sorted(daily_messages, key=lambda m: m.social_create_time)

# Global instance
analytics_service = AnalyticsService()

# Global instance
analytics_service = AnalyticsService()
