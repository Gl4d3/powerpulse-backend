"""
Service for calculating and caching all analytics, focusing on the new, expanded
Customer Satisfaction Index (CSI) model, calculated on a daily basis.
"""
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date
import numpy as np

from models import Conversation, Metric, Message, DailyAnalysis
from schemas import CSIMetricsResponse, DailyMetricsResponse, HistoricalMetricsResponse

logger = logging.getLogger(__name__)

# --- CSI Calculation Constants from gemini-refactor.md ---
CSI_PILLAR_WEIGHTS = {
    'effectiveness': 0.35,
    'effort': 0.25,
    'efficiency': 0.25,
    'empathy': 0.15,
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
            query = db.query(DailyAnalysis)
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
            
            # Calculate other core KPIs
            avg_sentiment = query.with_entities(func.avg(DailyAnalysis.sentiment_score)).scalar() or 0.0
            # CSAT: % of days where resolution was achieved (score > 7)
            csat_count = query.filter(DailyAnalysis.resolution_achieved > 7).count()
            csat_percentage = (csat_count / total_analyzed) * 100 if total_analyzed > 0 else 0.0
            # FCR: % of days where FCR score is high (> 7)
            fcr_count = query.filter(DailyAnalysis.fcr_score > 7).count()
            fcr_percentage = (fcr_count / total_analyzed) * 100 if total_analyzed > 0 else 0.0
            # Avg Response Time in minutes
            avg_response_time_seconds = query.with_entities(func.avg(DailyAnalysis.avg_response_time)).scalar() or 0.0
            avg_response_time_minutes = avg_response_time_seconds / 60

            # Sentiment Distribution
            total_sentiment_scores = query.filter(DailyAnalysis.sentiment_score.isnot(None)).count()
            if total_sentiment_scores > 0:
                positive_count = query.filter(DailyAnalysis.sentiment_score >= 7).count()
                negative_count = query.filter(DailyAnalysis.sentiment_score <= 4).count()
                neutral_count = total_sentiment_scores - positive_count - negative_count
                sentiment_distribution = {
                    "positive": positive_count / total_sentiment_scores,
                    "neutral": neutral_count / total_sentiment_scores,
                    "negative": negative_count / total_sentiment_scores,
                }
            else:
                sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}

            # Topic Frequency (This is a simplified aggregation)
            topic_results = db.query(Conversation.common_topics).filter(Conversation.common_topics.isnot(None)).all()
            topic_frequency = {}
            for topics_list in topic_results:
                for topic in topics_list[0]:
                    topic_frequency[topic] = topic_frequency.get(topic, 0) + 1
            
            topic_frequency_list = [{"topic": t, "frequency": f} for t, f in topic_frequency.items()]


            current_metrics = {
                "csi": overall_csi * 10, # Scale to 100
                "resolution_quality": avg_effectiveness * 10,
                "service_timeliness": avg_efficiency * 10,
                "customer_ease": avg_effort * 10,
                "interaction_quality": avg_empathy * 10,
                "sample_count": db.query(func.count(func.distinct(DailyAnalysis.conversation_id))).scalar(),
                "sentiment": avg_sentiment,
                "csat_percentage": csat_percentage,
                "fcr_percentage": fcr_percentage,
                "avg_response_time": avg_response_time_minutes,
                "sentiment_distribution": sentiment_distribution,
                "topic_frequency": topic_frequency_list,
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
            'sentiment': 0.0, 'csat_percentage': 0.0, 'fcr_percentage': 0.0,
            'avg_response_time': 0.0,
            'sentiment_distribution': {"positive": 0, "neutral": 0, "negative": 0},
            'topic_frequency': [], 'deltas': None, 'pillar_weights': CSI_PILLAR_WEIGHTS
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

# Global instance
analytics_service = AnalyticsService()

# Global instance
analytics_service = AnalyticsService()