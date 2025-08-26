"""
Service for calculating and caching all analytics, focusing on the new
Customer Satisfaction Index (CSI) and its four pillars.
"""
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date

from models import Conversation, Metric
from schemas import CSIMetricsResponse

logger = logging.getLogger(__name__)

# --- CSI Calculation Constants ---
CSI_WEIGHTS = {
    'effectiveness': 0.40,
    'effort': 0.25,
    'empathy': 0.20,
    'efficiency': 0.15,
}

def calculate_and_set_csi_score(conversation: Conversation):
    """
    Calculates the final CSI score for a single conversation based on its pillar scores.
    This function modifies the conversation object directly.
    """
    if not all([
        conversation.effectiveness_score is not None,
        conversation.effort_score is not None,
        conversation.empathy_score is not None,
        conversation.efficiency_score is not None
    ]):
        conversation.csi_score = None
        return

    csi_score = (
        (conversation.effectiveness_score * CSI_WEIGHTS['effectiveness']) +
        (conversation.effort_score * CSI_WEIGHTS['effort']) +
        (conversation.empathy_score * CSI_WEIGHTS['empathy']) +
        (conversation.efficiency_score * CSI_WEIGHTS['efficiency'])
    )
    conversation.csi_score = round(csi_score, 2)

class AnalyticsService:
    
    def calculate_and_cache_csi_metrics(self, db: Session) -> Dict[str, Any]:
        """Calculate all CSI-based metrics and cache them in the database."""
        try:
            total_analyzed = db.query(Conversation).filter(Conversation.csi_score.isnot(None)).count()

            if total_analyzed == 0:
                empty_metrics = self._get_empty_csi_metrics()
                self._cache_metrics(db, empty_metrics)
                return empty_metrics

            # Calculate average for each pillar and the overall CSI score
            avg_effectiveness = db.query(func.avg(Conversation.effectiveness_score)).scalar() or 0.0
            avg_efficiency = db.query(func.avg(Conversation.efficiency_score)).scalar() or 0.0
            avg_effort = db.query(func.avg(Conversation.effort_score)).scalar() or 0.0
            avg_empathy = db.query(func.avg(Conversation.empathy_score)).scalar() or 0.0
            overall_csi = db.query(func.avg(Conversation.csi_score)).scalar() or 0.0

            metrics = {
                'overall_csi_score': round(overall_csi, 2),
                'avg_effectiveness_score': round(avg_effectiveness, 2),
                'avg_efficiency_score': round(avg_efficiency, 2),
                'avg_effort_score': round(avg_effort, 2),
                'avg_empathy_score': round(avg_empathy, 2),
                'total_conversations_analyzed': total_analyzed,
                'last_updated': datetime.utcnow()
            }
            
            self._cache_metrics(db, metrics)
            logger.info(f"Calculated and cached CSI metrics: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating CSI metrics: {e}")
            raise

    def get_cached_csi_metrics(self, db: Session) -> CSIMetricsResponse:
        """Get CSI metrics from cache or calculate if not available or stale."""
        try:
            cached_metrics = {record.metric_name: record.metric_value for record in db.query(Metric).all()}
            
            required_metrics = [
                'overall_csi_score', 'avg_effectiveness_score', 'avg_efficiency_score',
                'avg_effort_score', 'avg_empathy_score', 'total_conversations_analyzed'
            ]
            
            if not all(metric in cached_metrics for metric in required_metrics):
                calculated_metrics = self.calculate_and_cache_csi_metrics(db)
                return CSIMetricsResponse(**calculated_metrics)

            return CSIMetricsResponse(
                overall_csi_score=cached_metrics.get('overall_csi_score', 0.0),
                avg_effectiveness_score=cached_metrics.get('avg_effectiveness_score', 0.0),
                avg_efficiency_score=cached_metrics.get('avg_efficiency_score', 0.0),
                avg_effort_score=cached_metrics.get('avg_effort_score', 0.0),
                avg_empathy_score=cached_metrics.get('avg_empathy_score', 0.0),
                total_conversations_analyzed=int(cached_metrics.get('total_conversations_analyzed', 0)),
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting cached CSI metrics: {e}")
            calculated_metrics = self.calculate_and_cache_csi_metrics(db)
            return CSIMetricsResponse(**calculated_metrics)

    def _cache_metrics(self, db: Session, metrics: Dict[str, Any]):
        """Cache calculated metrics in the database."""
        try:
            for key, value in metrics.items():
                if value is None: continue
                
                existing = db.query(Metric).filter(Metric.metric_name == key).first()
                metric_value = float(value) if isinstance(value, (int, float)) else 0
                metadata = None

                if isinstance(value, datetime):
                    metric_value = 0 # Dummy value for datetime
                    metadata = {"timestamp": value.isoformat()}
                
                if existing:
                    existing.metric_value = metric_value
                    existing.metric_metadata = metadata
                else:
                    db.add(Metric(metric_name=key, metric_value=metric_value, metric_metadata=metadata))
            
            db.commit()
            logger.info("CSI metrics cached successfully")
        except Exception as e:
            logger.error(f"Error caching CSI metrics: {e}")
            db.rollback()
            raise

    def _get_empty_csi_metrics(self) -> Dict[str, Any]:
        """Returns a dictionary with empty/zero values for CSI metrics."""
        return {
            'overall_csi_score': 0.0,
            'avg_effectiveness_score': 0.0,
            'avg_efficiency_score': 0.0,
            'avg_effort_score': 0.0,
            'avg_empathy_score': 0.0,
            'total_conversations_analyzed': 0,
            'last_updated': datetime.utcnow()
        }

# Global instance
analytics_service = AnalyticsService()