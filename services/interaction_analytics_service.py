"""
Interaction Analytics Service for PowerPulse CSI Analysis

This service analyzes detected interactions to calculate comprehensive CSI metrics,
identify patterns, and generate actionable insights for customer service improvement.

Key Features:
- CSI metric calculation (effectiveness, effort, efficiency, empathy)
- Interaction pattern analysis and trend detection
- Performance benchmarking and anomaly detection
- Actionable recommendations generation
- Multi-dimensional analytics (time-based, agent-based, topic-based)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import statistics
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from models import InteractionAnalysis, Conversation, Message
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

@dataclass
@dataclass
class CSIMetrics:
    """Container for calculated CSI metrics"""
    effectiveness_score: float = 0.0  # Resolution quality
    effort_score: float = 0.0        # Customer ease
    efficiency_score: float = 0.0    # Speed and productivity
    empathy_score: float = 0.0       # Emotional intelligence
    overall_csi: float = 0.0         # Combined CSI score
    confidence: float = 0.0          # Calculation confidence

@dataclass
class InteractionInsights:
    """Comprehensive analysis of interaction patterns"""
    total_interactions: int
    avg_duration: float
    resolution_rate: float
    sentiment_trends: Dict[str, float]
    complexity_distribution: Dict[str, int]
    peak_hours: List[int]
    common_issues: List[Dict[str, Any]]
    performance_gaps: List[str]
    recommendations: List[str]

@dataclass
class AnalyticsReport:
    """Complete analytics report for a time period"""
    period_start: datetime
    period_end: datetime
    total_interactions: int
    avg_csi_score: float
    metrics: CSIMetrics
    insights: InteractionInsights
    trends: Dict[str, List[float]]
    benchmarks: Dict[str, float]
    alerts: List[Dict[str, Any]]

class InteractionAnalyticsService:
    """
    Comprehensive analytics service for customer service interactions.
    Calculates CSI scores, identifies patterns, and generates actionable insights.
    """

    def __init__(self, gemini_service: GeminiService):
        self.gemini_service = gemini_service
        self.csi_weights = {
            'effectiveness': 0.30,  # 30% - Did we solve the problem?
            'effort': 0.25,        # 25% - How easy was it for customer?
            'efficiency': 0.25,    # 25% - How quickly was it resolved?
            'empathy': 0.20        # 20% - How well did we care?
        }

    async def analyze_interaction(self, db: Session, interaction: InteractionAnalysis) -> CSIMetrics:
        """
        CONSTITUTIONAL COMPLIANCE: Calculate comprehensive CSI metrics using AI micro-metrics extraction
        
        AMENDMENT I: AI micro-metrics extraction SHALL remain the authoritative method
        AMENDMENT II: ALL other pipeline logic SHALL remain identical to daily analysis
        
        Args:
            db: Database session
            interaction: InteractionAnalysis to analyze
            
        Returns:
            CSIMetrics with calculated scores from AI extraction
        """
        try:
            logger.info(f"CONSTITUTIONAL COMPLIANCE: Starting AI micro-metrics extraction for interaction {interaction.id}")
            
            # CONSTITUTIONAL REQUIREMENT: Use AI micro-metrics extraction (not rule-based)
            ai_micrometrics = await self._extract_ai_micrometrics([interaction])
            
            if not ai_micrometrics or interaction.id not in ai_micrometrics:
                logger.warning(f"No AI micro-metrics extracted for interaction {interaction.id}")
                return CSIMetrics()

            metrics_data = ai_micrometrics[interaction.id]
            
            # Extract AI-generated micro-metrics
            sentiment_score = metrics_data.get('sentiment_score', 5.0)
            sentiment_shift = metrics_data.get('sentiment_shift', 0.0)
            resolution_achieved = metrics_data.get('resolution_achieved', 5.0)
            fcr_score = metrics_data.get('fcr_score', 5.0)
            ces = metrics_data.get('ces', 4.0)
            common_topics = metrics_data.get('common_topics', [])

            # CONSTITUTIONAL REQUIREMENT: Use IDENTICAL four-pillars calculation as daily analysis
            from services.enhanced_analytics_service import enhanced_analytics_service
            
            # Temporarily set AI-extracted micro-metrics on interaction object
            interaction.sentiment_score = sentiment_score
            interaction.sentiment_shift = sentiment_shift
            interaction.resolution_achieved = resolution_achieved
            interaction.fcr_score = fcr_score
            interaction.ces = ces
            interaction.common_topics = common_topics
            
            # Calculate four-pillars using IDENTICAL methodology as daily analysis
            enhanced_analytics_service.calculate_and_set_csi_score(interaction)
            
            # Extract calculated pillar scores and CSI
            effectiveness = interaction.effectiveness_score or 0.0
            effort = interaction.effort_score or 0.0  
            efficiency = interaction.efficiency_score or 0.0
            empathy = interaction.empathy_score or 0.0
            overall_csi = interaction.csi_score or 0.0

            # Calculate AI inferred CSI (blackbox) for comparison
            try:
                messages = self._get_interaction_messages(db, interaction)
                messages_text = "\n".join([
                    f"{msg.social_create_time} - {msg.direction}: {msg.message_content}" 
                    for msg in messages
                ])
                interaction_context = f"Duration: {interaction.interaction_duration}min, Messages: {len(messages)}, Type: {interaction.interaction_type or 'general'}"
                inferred_csi = await self.gemini_service.infer_interaction_csi(messages_text, interaction_context)
                interaction.inferred_csi = inferred_csi
                
                logger.info(f"CONSTITUTIONAL COMPLIANCE: AI micro-metrics CSI: {overall_csi:.2f} vs AI blackbox CSI: {inferred_csi:.2f} for interaction {interaction.id}")
            except Exception as e:
                logger.warning(f"Failed to calculate AI inferred CSI for interaction {interaction.id}: {e}")
                interaction.inferred_csi = None

            # Commit all changes to database
            db.commit()

            # Calculate confidence based on data quality  
            confidence = self._calculate_confidence_from_ai_data(metrics_data)

            metrics = CSIMetrics(
                effectiveness_score=effectiveness,
                effort_score=effort,
                efficiency_score=efficiency,
                empathy_score=empathy,
                overall_csi=overall_csi,
                confidence=confidence
            )

            logger.info(f"CONSTITUTIONAL COMPLIANCE: Completed AI micro-metrics analysis for interaction {interaction.id}")
            return metrics

        except Exception as e:
            logger.error(f"Error in constitutional AI micro-metrics analysis for interaction {interaction.id}: {e}")
            return CSIMetrics()

    async def analyze_interactions_batch(self, db: Session, interactions: List[InteractionAnalysis]) -> Dict[int, CSIMetrics]:
        """
        CONSTITUTIONAL COMPLIANCE: Batch analysis of multiple interactions using AI micro-metrics extraction
        
        This method processes multiple interactions in a single AI call for performance,
        while maintaining constitutional compliance with AI micro-metrics extraction.
        
        Args:
            db: Database session
            interactions: List of InteractionAnalysis objects to analyze
            
        Returns:
            Dictionary mapping interaction_id to CSIMetrics
        """
        if not interactions:
            return {}
            
        try:
            logger.info(f"CONSTITUTIONAL COMPLIANCE: Starting batch AI micro-metrics extraction for {len(interactions)} interactions")
            
            # CONSTITUTIONAL REQUIREMENT: Use AI micro-metrics extraction for entire batch
            ai_micrometrics = await self._extract_ai_micrometrics(interactions)
            
            # Process results for each interaction
            results = {}
            for interaction in interactions:
                if interaction.id in ai_micrometrics:
                    metrics_data = ai_micrometrics[interaction.id]
                    
                    # Extract AI-generated micro-metrics
                    sentiment_score = metrics_data.get('sentiment_score', 5.0)
                    sentiment_shift = metrics_data.get('sentiment_shift', 0.0)
                    resolution_achieved = metrics_data.get('resolution_achieved', 5.0)
                    fcr_score = metrics_data.get('fcr_score', 5.0)
                    ces = metrics_data.get('ces', 4.0)
                    common_topics = metrics_data.get('common_topics', [])

                    # CONSTITUTIONAL REQUIREMENT: Use IDENTICAL four-pillars calculation as daily analysis
                    from services.enhanced_analytics_service import enhanced_analytics_service
                    
                    # Temporarily set AI-extracted micro-metrics on interaction object
                    interaction.sentiment_score = sentiment_score
                    interaction.sentiment_shift = sentiment_shift
                    interaction.resolution_achieved = resolution_achieved
                    interaction.fcr_score = fcr_score
                    interaction.ces = ces
                    interaction.common_topics = common_topics

                    # Calculate four-pillars CSI using enhanced analytics service
                    enhanced_analytics_service.calculate_and_set_csi_score(interaction)
                    csi_result = CSIMetrics(
                        overall_csi=interaction.csi_score or 0.0,
                        effectiveness_score=interaction.effectiveness_score or 0.0,
                        effort_score=interaction.effort_score or 0.0,
                        efficiency_score=interaction.efficiency_score or 0.0,
                        empathy_score=interaction.empathy_score or 0.0,
                        confidence=0.9  # Default confidence for calculated CSI
                    )
                    
                    results[interaction.id] = csi_result
                else:
                    logger.warning(f"No AI micro-metrics extracted for interaction {interaction.id}")
                    results[interaction.id] = CSIMetrics()
            
            logger.info(f"CONSTITUTIONAL COMPLIANCE: Completed batch analysis for {len(results)} interactions")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch interaction analysis: {e}")
            # Return empty results for all interactions
            return {interaction.id: CSIMetrics() for interaction in interactions}

    async def _extract_ai_micrometrics(self, interactions: List[InteractionAnalysis]) -> Dict[int, Dict[str, Any]]:
        """
        CONSTITUTIONAL REQUIREMENT: Extract micro-metrics using AI (mirrors daily analysis approach)
        
        Returns: Dictionary mapping interaction_id to micro-metrics data
        """
        try:
            logger.info(f"CONSTITUTIONAL COMPLIANCE: Extracting AI micro-metrics for {len(interactions)} interactions")
            
            # Use constitutional AI micro-metrics extraction
            analysis_results, missed_ids, usage_metadata, response_text = await self.gemini_service.analyze_interaction_analyses_batch(interactions)
            
            # Parse results into dictionary format
            micrometrics_map = {}
            for result in analysis_results:
                interaction_id = result.get('interaction_analysis_id')
                interaction_analysis = result.get('interaction_analysis', {})
                
                if interaction_id:
                    micrometrics_map[interaction_id] = interaction_analysis
            
            logger.info(f"CONSTITUTIONAL COMPLIANCE: Successfully extracted AI micro-metrics for {len(micrometrics_map)} interactions")
            return micrometrics_map
            
        except Exception as e:
            logger.error(f"Error extracting AI micro-metrics: {e}")
            return {}

    def _calculate_confidence_from_ai_data(self, metrics_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on AI-extracted data quality"""
        try:
            # Count how many micro-metrics were successfully extracted
            required_metrics = ['sentiment_score', 'sentiment_shift', 'resolution_achieved', 'fcr_score', 'ces']
            extracted_count = sum(1 for metric in required_metrics if metrics_data.get(metric) is not None)
            
            # Base confidence on completeness of AI extraction
            base_confidence = extracted_count / len(required_metrics)
            
            # Adjust based on data reasonableness
            sentiment_score = metrics_data.get('sentiment_score', 5.0)
            if 0 <= sentiment_score <= 10:
                base_confidence += 0.1
            
            ces = metrics_data.get('ces', 4.0)
            if 1 <= ces <= 7:
                base_confidence += 0.1
            
            return min(1.0, max(0.0, base_confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5

    # CONSTITUTIONAL AMENDMENT I: Rule-based micro-metrics calculations REMOVED
    # All effectiveness, effort, efficiency, and empathy calculations now use AI extraction via _extract_ai_micrometrics()
    # This ensures consistency with daily analysis pipeline and maintains constitutional compliance

    def _get_interaction_messages(self, db: Session, interaction: InteractionAnalysis) -> List[Message]:
        """Get all messages for an interaction"""
        return db.query(Message).filter(
            and_(
                Message.conversation_id == interaction.conversation_id,
                Message.id >= interaction.start_message_id,
                Message.id <= interaction.end_message_id
            )
        ).order_by(Message.social_create_time).all()

    # CONSTITUTIONAL COMPLIANCE: Old rule-based confidence calculation removed
    # Now using _calculate_confidence_from_ai_data() method for AI-based confidence assessment

    def _detect_repetition(self, customer_messages: List[Message]) -> float:
        """Detect repetitive content in customer messages"""
        if len(customer_messages) < 2:
            return 0.0
        
        # Simple keyword overlap detection
        repetition_score = 0.0
        for i in range(1, len(customer_messages)):
            words_current = set(customer_messages[i].message_content.lower().split())
            words_previous = set(customer_messages[i-1].message_content.lower().split())
            
            if len(words_current) > 0:
                overlap = len(words_current & words_previous) / len(words_current)
                if overlap > 0.5:  # 50% word overlap
                    repetition_score += 1.0
                    
        return repetition_score

    # CONSTITUTIONAL COMPLIANCE: Old mixed rule-based/AI assessment methods removed
    # All assessment now uses pure AI micro-metrics extraction via analyze_interaction_analyses_batch()

    async def generate_period_report(self, db: Session, start_date: datetime, end_date: datetime) -> AnalyticsReport:
        """Generate comprehensive analytics report for a time period"""
        try:
            # Get all interactions in period
            interactions = db.query(InteractionAnalysis).filter(
                and_(
                    InteractionAnalysis.interaction_start >= start_date,
                    InteractionAnalysis.interaction_end <= end_date
                )
            ).all()

            if not interactions:
                logger.warning(f"No interactions found for period {start_date} to {end_date}")
                return AnalyticsReport(
                    period_start=start_date,
                    period_end=end_date,
                    total_interactions=0,
                    avg_csi_score=0.0,
                    metrics=CSIMetrics(),
                    insights=InteractionInsights(
                        total_interactions=0,
                        avg_duration=0.0,
                        resolution_rate=0.0,
                        sentiment_trends={},
                        complexity_distribution={},
                        peak_hours=[],
                        common_issues=[],
                        performance_gaps=[],
                        recommendations=[]
                    ),
                    trends={},
                    benchmarks={},
                    alerts=[]
                )

            # Calculate period metrics
            metrics = await self._calculate_period_metrics(interactions)
            insights = await self._analyze_period_insights(db, interactions)
            trends = self._calculate_trends(interactions)
            benchmarks = self._calculate_benchmarks(interactions)
            alerts = self._generate_alerts(interactions, benchmarks)

            # Calculate average CSI
            csi_scores = [i.csi_score for i in interactions if i.csi_score is not None]
            avg_csi = statistics.mean(csi_scores) if csi_scores else 0.0

            report = AnalyticsReport(
                period_start=start_date,
                period_end=end_date,
                total_interactions=len(interactions),
                avg_csi_score=avg_csi,
                metrics=metrics,
                insights=insights,
                trends=trends,
                benchmarks=benchmarks,
                alerts=alerts
            )

            logger.info(f"Generated analytics report: {len(interactions)} interactions, avg CSI: {avg_csi:.2f}")
            return report

        except Exception as e:
            logger.error(f"Error generating period report: {e}")
            return AnalyticsReport(
                period_start=start_date,
                period_end=end_date,
                total_interactions=0,
                avg_csi_score=0.0,
                metrics=CSIMetrics(),
                insights=InteractionInsights(
                    total_interactions=0,
                    avg_duration=0.0,
                    resolution_rate=0.0,
                    sentiment_trends={},
                    complexity_distribution={},
                    peak_hours=[],
                    common_issues=[],
                    performance_gaps=[],
                    recommendations=[]
                ),
                trends={},
                benchmarks={},
                alerts=[]
            )

    async def _calculate_period_metrics(self, interactions: List[InteractionAnalysis]) -> CSIMetrics:
        """Calculate aggregated metrics for all interactions in period"""
        if not interactions:
            return CSIMetrics()

        # Filter interactions with scores
        scored_interactions = [i for i in interactions if i.csi_score is not None]
        
        if not scored_interactions:
            return CSIMetrics()

        # Calculate averages
        effectiveness_scores = [i.effectiveness_score for i in scored_interactions if i.effectiveness_score is not None]
        effort_scores = [i.effort_score for i in scored_interactions if i.effort_score is not None]
        efficiency_scores = [i.efficiency_score for i in scored_interactions if i.efficiency_score is not None]
        empathy_scores = [i.empathy_score for i in scored_interactions if i.empathy_score is not None]
        csi_scores = [i.csi_score for i in scored_interactions if i.csi_score is not None]

        return CSIMetrics(
            effectiveness_score=statistics.mean(effectiveness_scores) if effectiveness_scores else 0.0,
            effort_score=statistics.mean(effort_scores) if effort_scores else 0.0,
            efficiency_score=statistics.mean(efficiency_scores) if efficiency_scores else 0.0,
            empathy_score=statistics.mean(empathy_scores) if empathy_scores else 0.0,
            overall_csi=statistics.mean(csi_scores) if csi_scores else 0.0,
            confidence=0.85  # High confidence for aggregated data
        )

    async def _analyze_period_insights(self, db: Session, interactions: List[InteractionAnalysis]) -> InteractionInsights:
        """Generate comprehensive insights from interaction data"""
        if not interactions:
            return InteractionInsights(
                total_interactions=0,
                avg_duration=0.0,
                resolution_rate=0.0,
                sentiment_trends={},
                complexity_distribution={},
                peak_hours=[],
                common_issues=[],
                performance_gaps=[],
                recommendations=[]
            )

        # Basic statistics
        total_interactions = len(interactions)
        durations = [i.interaction_duration for i in interactions if i.interaction_duration is not None]
        avg_duration = statistics.mean(durations) if durations else 0.0

        # Resolution rate (high CSI score indicates resolution)
        high_csi_count = sum(1 for i in interactions if i.csi_score and i.csi_score >= 7.0)
        resolution_rate = (high_csi_count / total_interactions) if total_interactions > 0 else 0.0

        # Sentiment trends
        sentiment_scores = [i.sentiment_score for i in interactions if i.sentiment_score is not None]
        sentiment_trends = {
            'positive': sum(1 for s in sentiment_scores if s >= 4.0) / len(sentiment_scores) if sentiment_scores else 0.0,
            'neutral': sum(1 for s in sentiment_scores if 2.0 <= s < 4.0) / len(sentiment_scores) if sentiment_scores else 0.0,
            'negative': sum(1 for s in sentiment_scores if s < 2.0) / len(sentiment_scores) if sentiment_scores else 0.0
        }

        # Complexity distribution
        complexities = [i.interaction_complexity for i in interactions if i.interaction_complexity]
        complexity_distribution = dict(Counter(complexities))

        # Peak hours analysis
        hours = [i.interaction_start.hour for i in interactions if i.interaction_start]
        hour_counts = Counter(hours)
        peak_hours = [hour for hour, count in hour_counts.most_common(3)]

        # Common issues (placeholder - would need more sophisticated topic analysis)
        common_issues = []

        # Performance gaps
        performance_gaps = []
        low_csi_interactions = [i for i in interactions if i.csi_score and i.csi_score < 5.0]
        if len(low_csi_interactions) / total_interactions > 0.2:
            performance_gaps.append("High percentage of low-scoring interactions")

        # Recommendations
        recommendations = await self._generate_recommendations(interactions)

        return InteractionInsights(
            total_interactions=total_interactions,
            avg_duration=avg_duration,
            resolution_rate=resolution_rate,
            sentiment_trends=sentiment_trends,
            complexity_distribution=complexity_distribution,
            peak_hours=peak_hours,
            common_issues=common_issues,
            performance_gaps=performance_gaps,
            recommendations=recommendations
        )

    def _calculate_trends(self, interactions: List[InteractionAnalysis]) -> Dict[str, List[float]]:
        """Calculate trends over time"""
        # Group by day and calculate daily averages
        daily_scores = defaultdict(list)
        
        for interaction in interactions:
            if interaction.csi_score and interaction.interaction_start:
                day_key = interaction.interaction_start.date()
                daily_scores[day_key].append(interaction.csi_score)
        
        # Calculate daily averages
        daily_averages = {}
        for day, scores in daily_scores.items():
            daily_averages[day.isoformat()] = statistics.mean(scores)
        
        return {
            'daily_csi': list(daily_averages.values())
        }

    def _calculate_benchmarks(self, interactions: List[InteractionAnalysis]) -> Dict[str, float]:
        """Calculate performance benchmarks"""
        csi_scores = [i.csi_score for i in interactions if i.csi_score is not None]
        durations = [i.interaction_duration for i in interactions if i.interaction_duration is not None]
        
        return {
            'target_csi': 8.0,
            'current_csi': statistics.mean(csi_scores) if csi_scores else 0.0,
            'target_duration': 15.0,  # 15 minutes
            'current_duration': statistics.mean(durations) if durations else 0.0,
            'target_resolution_rate': 0.85,
            'current_resolution_rate': sum(1 for s in csi_scores if s >= 7.0) / len(csi_scores) if csi_scores else 0.0
        }

    def _generate_alerts(self, interactions: List[InteractionAnalysis], benchmarks: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate performance alerts"""
        alerts = []
        
        # CSI below target
        if benchmarks['current_csi'] < benchmarks['target_csi']:
            alerts.append({
                'type': 'performance',
                'severity': 'high' if benchmarks['current_csi'] < 6.0 else 'medium',
                'message': f"CSI score ({benchmarks['current_csi']:.1f}) is below target ({benchmarks['target_csi']:.1f})",
                'metric': 'csi_score'
            })
        
        # Long interaction duration
        if benchmarks['current_duration'] > benchmarks['target_duration'] * 1.5:
            alerts.append({
                'type': 'efficiency',
                'severity': 'medium',
                'message': f"Average interaction duration ({benchmarks['current_duration']:.1f}min) exceeds target",
                'metric': 'duration'
            })
        
        # Low resolution rate
        if benchmarks['current_resolution_rate'] < benchmarks['target_resolution_rate']:
            alerts.append({
                'type': 'effectiveness',
                'severity': 'high',
                'message': f"Resolution rate ({benchmarks['current_resolution_rate']:.1%}) below target",
                'metric': 'resolution_rate'
            })
        
        return alerts

    async def _generate_recommendations(self, interactions: List[InteractionAnalysis]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Analyze common patterns
        csi_scores = [i.csi_score for i in interactions if i.csi_score is not None]
        durations = [i.interaction_duration for i in interactions if i.interaction_duration is not None]
        
        if csi_scores:
            avg_csi = statistics.mean(csi_scores)
            
            if avg_csi < 6.0:
                recommendations.append("Focus on agent training for problem resolution skills")
                recommendations.append("Review and improve standard operating procedures")
            
            if durations and statistics.mean(durations) > 20:
                recommendations.append("Implement knowledge base improvements to reduce interaction time")
                recommendations.append("Provide agents with better diagnostic tools")
        
        # AI enhancement usage
        ai_enhanced = sum(1 for i in interactions if 'ai' in (i.boundary_method or '').lower())
        if ai_enhanced / len(interactions) < 0.5:
            recommendations.append("Increase AI enhancement usage for better interaction detection")
        
        return recommendations