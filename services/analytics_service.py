import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta, date

from models import Message, Conversation, Metric
from schemas import MetricsResponse

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        pass
    
    def calculate_and_cache_metrics(self, db: Session) -> Dict[str, Any]:
        """Calculate all metrics and cache them in the database"""
        try:
            metrics = {}
            
            # Basic counts
            total_conversations = db.query(Conversation).count()
            total_messages = db.query(Message).count()
            
            if total_conversations == 0:
                # Return empty metrics if no data
                empty_metrics = {
                    'avg_sentiment_score': 0.0,
                    'csat_percentage': 0.0,
                    'fcr_percentage': 0.0,
                    'avg_response_time_minutes': 0.0,
                    'total_conversations': 0,
                    'total_messages': 0,
                    'most_common_topics': [],
                    'last_updated': datetime.utcnow()
                }
                self._cache_metrics(db, empty_metrics)
                return empty_metrics
            
            # Average sentiment score
            avg_sentiment = db.query(func.avg(Conversation.avg_sentiment)).filter(
                Conversation.avg_sentiment.isnot(None)
            ).scalar() or 0.0
            
            # CSAT percentage (conversations with satisfaction >= 4 or is_satisfied = True)
            satisfied_count = db.query(Conversation).filter(
                and_(
                    Conversation.is_satisfied == True,
                    Conversation.satisfaction_score.isnot(None)
                )
            ).count()
            
            csat_percentage = (satisfied_count / total_conversations) * 100 if total_conversations > 0 else 0.0
            
            # FCR percentage
            fcr_count = db.query(Conversation).filter(
                Conversation.first_contact_resolution == True
            ).count()
            
            fcr_percentage = (fcr_count / total_conversations) * 100 if total_conversations > 0 else 0.0
            
            # Average response time
            avg_response_time = db.query(func.avg(Conversation.avg_response_time_minutes)).filter(
                Conversation.avg_response_time_minutes.isnot(None)
            ).scalar() or 0.0
            
            # Most common topics
            most_common_topics = self._get_most_common_topics(db)
            
            metrics = {
                'avg_sentiment_score': round(avg_sentiment, 2),
                'csat_percentage': round(csat_percentage, 2),
                'fcr_percentage': round(fcr_percentage, 2),
                'avg_response_time_minutes': round(avg_response_time, 2),
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'most_common_topics': most_common_topics,
                'last_updated': datetime.utcnow()
            }
            
            # Cache metrics in database
            self._cache_metrics(db, metrics)
            
            logger.info(f"Calculated and cached metrics: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            raise
    
    def get_cached_metrics(self, db: Session) -> MetricsResponse:
        """Get metrics from cache or calculate if not available"""
        try:
            # Try to get from cache first
            cached_metrics = {}
            
            metric_records = db.query(Metric).all()
            for record in metric_records:
                cached_metrics[record.metric_name] = record.metric_value
            
            # Check if we have all required metrics and they're recent
            required_metrics = [
                'avg_sentiment_score', 'csat_percentage', 'fcr_percentage',
                'avg_response_time_minutes', 'total_conversations', 'total_messages'
            ]
            
            has_all_metrics = all(metric in cached_metrics for metric in required_metrics)
            
            # Get last update time
            last_updated_record = db.query(Metric).filter(
                Metric.metric_name == 'last_updated'
            ).first()
            
            is_recent = False
            if last_updated_record and last_updated_record.metric_metadata:
                timestamp_str = last_updated_record.metric_metadata.get('timestamp')
                if timestamp_str:
                    last_updated = datetime.fromisoformat(timestamp_str)
                    is_recent = (datetime.utcnow() - last_updated).total_seconds() < 3600  # 1 hour
            
            if not has_all_metrics or not is_recent:
                # Recalculate metrics
                return self.calculate_and_cache_metrics(db)
            
            # Get topics from cache
            topics_record = db.query(Metric).filter(
                Metric.metric_name == 'most_common_topics'
            ).first()
            
            most_common_topics = []
            if topics_record and topics_record.metric_metadata:
                most_common_topics = topics_record.metric_metadata.get('topics', [])
            
            return MetricsResponse(
                avg_sentiment_score=cached_metrics.get('avg_sentiment_score', 0.0),
                csat_percentage=cached_metrics.get('csat_percentage', 0.0),
                fcr_percentage=cached_metrics.get('fcr_percentage', 0.0),
                avg_response_time_minutes=cached_metrics.get('avg_response_time_minutes', 0.0),
                total_conversations=int(cached_metrics.get('total_conversations', 0)),
                total_messages=int(cached_metrics.get('total_messages', 0)),
                most_common_topics=most_common_topics,
                last_updated=datetime.utcnow()  # Use current time as fallback
            )
            
        except Exception as e:
            logger.error(f"Error getting cached metrics: {e}")
            # Fallback to calculation
            return self.calculate_and_cache_metrics(db)
    
    def _get_most_common_topics(self, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """Extract most common topics across all conversations"""
        try:
            # Get all topics from conversations
            conversations_with_topics = db.query(Conversation.common_topics).filter(
                Conversation.common_topics.isnot(None)
            ).all()
            
            topic_counts = {}
            
            for (topics_json,) in conversations_with_topics:
                if topics_json:
                    topics = topics_json if isinstance(topics_json, list) else []
                    for topic in topics:
                        if isinstance(topic, str) and topic.strip():
                            topic_clean = topic.strip().lower()
                            topic_counts[topic_clean] = topic_counts.get(topic_clean, 0) + 1
            
            # Sort by frequency and return top topics
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            
            return [
                {"topic": topic, "count": count, "percentage": round((count / len(conversations_with_topics)) * 100, 1)}
                for topic, count in sorted_topics[:limit]
            ]
            
        except Exception as e:
            logger.error(f"Error getting common topics: {e}")
            return []
    
    def _cache_metrics(self, db: Session, metrics: Dict[str, Any]):
        """Cache calculated metrics in database"""
        try:
            for key, value in metrics.items():
                existing = db.query(Metric).filter(Metric.metric_name == key).first()

                if key == 'most_common_topics':
                    # Store topics in metadata
                    if existing:
                        existing.metric_value = len(value)
                        existing.metric_metadata = {"topics": value}
                    else:
                        db.add(Metric(
                            metric_name=key,
                            metric_value=len(value),
                            metric_metadata={"topics": value}
                        ))
                elif key == 'last_updated':
                    # Store datetime as string
                    timestamp_str = value.isoformat() if isinstance(value, datetime) else str(value)
                    if existing:
                        existing.metric_value = 0  # Dummy value
                        existing.metric_metadata = {"timestamp": timestamp_str}
                    else:
                        db.add(Metric(
                            metric_name=key,
                            metric_value=0,  # Dummy value
                            metric_metadata={"timestamp": timestamp_str}
                        ))
                else:
                    # Store numeric metrics
                    numeric_value = float(value)
                    if existing:
                        existing.metric_value = numeric_value
                        existing.metric_metadata = None
                    else:
                        db.add(Metric(
                            metric_name=key,
                            metric_value=numeric_value,
                            metric_metadata=None
                        ))
            
            db.commit()
            logger.info("Metrics cached successfully")
            
        except Exception as e:
            logger.error(f"Error caching metrics: {e}")
            db.rollback()
            raise

    def calculate_metrics_with_date_filter(self, db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        """Calculate metrics with date filtering applied"""
        try:
            # Build base query for conversations
            conv_query = db.query(Conversation)
            msg_query = db.query(Message)
            
            # Apply date filtering
            if start_date:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                conv_query = conv_query.filter(Conversation.first_message_time >= start_datetime)
                msg_query = msg_query.filter(Message.social_create_time >= start_datetime)
            
            if end_date:
                end_datetime = datetime.combine(end_date, datetime.max.time())
                conv_query = conv_query.filter(Conversation.last_message_time <= end_datetime)
                msg_query = msg_query.filter(Message.social_create_time <= end_datetime)
            
            # Basic counts
            total_conversations = conv_query.count()
            total_messages = msg_query.count()
            
            if total_conversations == 0:
                return {
                    'avg_sentiment_score': 0.0,
                    'csat_percentage': 0.0,
                    'fcr_percentage': 0.0,
                    'avg_response_time_minutes': 0.0,
                    'total_conversations': 0,
                    'total_messages': 0,
                    'most_common_topics': [],
                    'last_updated': datetime.utcnow()
                }
            
            # Average sentiment score
            avg_sentiment = conv_query.with_entities(func.avg(Conversation.avg_sentiment)).filter(
                Conversation.avg_sentiment.isnot(None)
            ).scalar() or 0.0
            
            # CSAT percentage
            satisfied_count = conv_query.filter(
                and_(
                    Conversation.is_satisfied == True,
                    Conversation.satisfaction_score.isnot(None)
                )
            ).count()
            
            csat_percentage = (satisfied_count / total_conversations) * 100 if total_conversations > 0 else 0.0
            
            # FCR percentage
            fcr_count = conv_query.filter(Conversation.first_contact_resolution == True).count()
            fcr_percentage = (fcr_count / total_conversations) * 100 if total_conversations > 0 else 0.0
            
            # Average response time
            avg_response_time = conv_query.with_entities(func.avg(Conversation.avg_response_time_minutes)).filter(
                Conversation.avg_response_time_minutes.isnot(None)
            ).scalar() or 0.0
            
            # Most common topics for filtered conversations
            filtered_conversations = conv_query.filter(Conversation.common_topics.isnot(None)).all()
            most_common_topics = self._extract_topics_from_conversations(filtered_conversations)
            
            return {
                'avg_sentiment_score': round(avg_sentiment, 2),
                'csat_percentage': round(csat_percentage, 2),
                'fcr_percentage': round(fcr_percentage, 2),
                'avg_response_time_minutes': round(avg_response_time, 2),
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'most_common_topics': most_common_topics,
                'last_updated': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics with date filter: {e}")
            raise
    
    def _extract_topics_from_conversations(self, conversations: List[Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Extract and count topics from a list of conversation objects"""
        try:
            topic_counts = {}
            
            for conv in conversations:
                if conv.common_topics:
                    topics = conv.common_topics if isinstance(conv.common_topics, list) else []
                    for topic in topics:
                        if isinstance(topic, str) and topic.strip():
                            topic_clean = topic.strip().lower()
                            topic_counts[topic_clean] = topic_counts.get(topic_clean, 0) + 1
            
            # Sort by frequency and return top topics
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            total_conversations = len(conversations)
            
            return [
                {"topic": topic, "count": count, "percentage": round((count / total_conversations) * 100, 1)}
                for topic, count in sorted_topics[:limit]
            ] if total_conversations > 0 else []
            
        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return []

# Global instance
analytics_service = AnalyticsService()
