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
        Calculate comprehensive CSI metrics for a single interaction.
        
        Args:
            db: Database session
            interaction: InteractionAnalysis to analyze
            
        Returns:
            CSIMetrics with calculated scores
        """
        try:
            # Get interaction messages
            messages = self._get_interaction_messages(db, interaction)
            
            if not messages:
                logger.warning(f"No messages found for interaction {interaction.id}")
                return CSIMetrics()

            # Calculate individual pillar scores
            effectiveness = await self._calculate_effectiveness(messages, interaction)
            effort = await self._calculate_effort(messages, interaction)
            efficiency = await self._calculate_efficiency(messages, interaction)
            empathy = await self._calculate_empathy(messages, interaction)

            # Calculate overall CSI score
            overall_csi = (
                effectiveness * self.csi_weights['effectiveness'] +
                effort * self.csi_weights['effort'] +
                efficiency * self.csi_weights['efficiency'] +
                empathy * self.csi_weights['empathy']
            )

            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(messages, interaction)

            metrics = CSIMetrics(
                effectiveness_score=effectiveness,
                effort_score=effort,
                efficiency_score=efficiency,
                empathy_score=empathy,
                overall_csi=overall_csi,
                confidence=confidence
            )

            # Update interaction record
            interaction.effectiveness_score = effectiveness
            interaction.effort_score = effort
            interaction.efficiency_score = efficiency
            interaction.empathy_score = empathy
            interaction.csi_score = overall_csi
            db.commit()

            logger.info(f"Calculated CSI metrics for interaction {interaction.id}: {overall_csi:.2f}")
            return metrics

        except Exception as e:
            logger.error(f"Error analyzing interaction {interaction.id}: {e}")
            return CSIMetrics()

    async def _calculate_effectiveness(self, messages: List[Message], interaction: InteractionAnalysis) -> float:
        """Calculate effectiveness score (resolution quality)"""
        try:
            score = 5.0  # Start with baseline

            # Check for resolution indicators
            resolution_keywords = [
                'resolved', 'fixed', 'solved', 'completed', 'done',
                'working now', 'thank you', 'problem sorted'
            ]
            
            agent_messages = [m for m in messages if m.direction == 'to_client']
            customer_messages = [m for m in messages if m.direction == 'to_company']

            # Resolution indication boost
            last_messages = messages[-3:] if len(messages) >= 3 else messages
            for msg in last_messages:
                content_lower = msg.message_content.lower()
                if any(keyword in content_lower for keyword in resolution_keywords):
                    score += 1.5

            # Customer satisfaction indicators
            positive_indicators = ['thank', 'great', 'perfect', 'excellent', 'appreciate']
            for msg in customer_messages:
                content_lower = msg.message_content.lower()
                if any(indicator in content_lower for indicator in positive_indicators):
                    score += 1.0

            # Multi-turn penalty (complexity might indicate difficulty)
            if len(messages) > 8:
                score -= 0.5
            elif len(messages) > 15:
                score -= 1.0

            # Use AI for resolution assessment if available
            if len(messages) >= 3:
                ai_assessment = await self._ai_assess_resolution(messages)
                if ai_assessment:
                    score = (score + ai_assessment) / 2  # Blend rule-based and AI scores

            return max(0.0, min(10.0, score))

        except Exception as e:
            logger.error(f"Error calculating effectiveness: {e}")
            return 5.0

    async def _calculate_effort(self, messages: List[Message], interaction: InteractionAnalysis) -> float:
        """Calculate effort score (customer ease)"""
        try:
            score = 8.0  # Start high (low effort is good)

            # Message count penalty (more messages = more effort)
            message_penalty = len(messages) * 0.2
            score -= message_penalty

            # Duration penalty 
            if interaction.interaction_duration:
                if interaction.interaction_duration > 30:  # 30+ minutes
                    score -= 2.0
                elif interaction.interaction_duration > 15:  # 15-30 minutes
                    score -= 1.0

            # Repetition detection
            customer_messages = [m for m in messages if m.direction == 'to_company']
            if len(customer_messages) > 1:
                repetition_penalty = self._detect_repetition(customer_messages) * 0.5
                score -= repetition_penalty

            # Transfer/escalation penalty
            transfer_keywords = ['transfer', 'escalate', 'supervisor', 'manager', 'specialist']
            for msg in messages:
                if any(keyword in msg.message_content.lower() for keyword in transfer_keywords):
                    score -= 1.5

            return max(0.0, min(10.0, score))

        except Exception as e:
            logger.error(f"Error calculating effort: {e}")
            return 5.0

    async def _calculate_efficiency(self, messages: List[Message], interaction: InteractionAnalysis) -> float:
        """Calculate efficiency score (speed and productivity)"""
        try:
            score = 7.0  # Start with baseline

            # First response time boost
            if interaction.first_response_time:
                if interaction.first_response_time < 300:  # < 5 minutes
                    score += 2.0
                elif interaction.first_response_time < 900:  # < 15 minutes
                    score += 1.0
                elif interaction.first_response_time > 3600:  # > 1 hour
                    score -= 2.0

            # Average response time assessment
            if interaction.avg_response_time:
                if interaction.avg_response_time < 600:  # < 10 minutes
                    score += 1.0
                elif interaction.avg_response_time > 1800:  # > 30 minutes
                    score -= 1.5

            # Total handling time efficiency
            if interaction.total_handling_time:
                if interaction.total_handling_time < 5:  # < 5 minutes total
                    score += 1.5
                elif interaction.total_handling_time > 60:  # > 1 hour total
                    score -= 2.0

            # Message efficiency (fewer back-and-forth is better)
            turns = interaction.turns_count or len(messages) // 2
            if turns <= 2:
                score += 1.5
            elif turns > 6:
                score -= 1.0

            return max(0.0, min(10.0, score))

        except Exception as e:
            logger.error(f"Error calculating efficiency: {e}")
            return 5.0

    async def _calculate_empathy(self, messages: List[Message], interaction: InteractionAnalysis) -> float:
        """Calculate empathy score (emotional intelligence)"""
        try:
            score = 5.0  # Start with baseline

            agent_messages = [m for m in messages if m.direction == 'to_client']
            
            # Positive sentiment from agents
            for msg in agent_messages:
                if msg.sentiment_score and msg.sentiment_score > 3.5:
                    score += 0.5

            # Empathy keywords detection
            empathy_keywords = [
                'sorry', 'apologize', 'understand', 'appreciate', 'thank',
                'help', 'assist', 'concern', 'frustrated', 'inconvenience'
            ]
            
            for msg in agent_messages:
                content_lower = msg.message_content.lower()
                empathy_count = sum(1 for keyword in empathy_keywords if keyword in content_lower)
                score += empathy_count * 0.3

            # Personal touch indicators
            personal_keywords = ['name', 'personally', 'specifically for you', 'your situation']
            for msg in agent_messages:
                content_lower = msg.message_content.lower()
                if any(keyword in content_lower for keyword in personal_keywords):
                    score += 0.8

            # Use AI for empathy assessment
            if agent_messages:
                ai_empathy = await self._ai_assess_empathy(agent_messages)
                if ai_empathy:
                    score = (score + ai_empathy) / 2

            return max(0.0, min(10.0, score))

        except Exception as e:
            logger.error(f"Error calculating empathy: {e}")
            return 5.0

    def _get_interaction_messages(self, db: Session, interaction: InteractionAnalysis) -> List[Message]:
        """Get all messages for an interaction"""
        return db.query(Message).filter(
            and_(
                Message.conversation_id == interaction.conversation_id,
                Message.id >= interaction.start_message_id,
                Message.id <= interaction.end_message_id
            )
        ).order_by(Message.social_create_time).all()

    def _calculate_confidence(self, messages: List[Message], interaction: InteractionAnalysis) -> float:
        """Calculate confidence score based on data quality"""
        confidence = 0.7  # Base confidence
        
        # Data completeness boosts
        if interaction.sentiment_score is not None:
            confidence += 0.1
        if interaction.total_handling_time is not None:
            confidence += 0.1
        if len(messages) >= 3:
            confidence += 0.1
        
        # AI enhancement boost
        if 'ai' in (interaction.boundary_method or '').lower():
            confidence += 0.1
            
        return min(1.0, confidence)

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

    async def _ai_assess_resolution(self, messages: List[Message]) -> Optional[float]:
        """Use AI to assess interaction resolution quality"""
        try:
            # Create conversation context
            conversation = "\n".join([
                f"{'Agent' if msg.direction == 'to_client' else 'Customer'}: {msg.message_content}"
                for msg in messages
            ])
            
            prompt = f"""Analyze this customer service interaction for resolution quality.

Conversation:
{conversation}

Rate the resolution effectiveness on a scale of 0-10, considering:
- Was the customer's issue fully addressed?
- Did the customer express satisfaction?
- Was the solution appropriate and complete?
- Did the interaction end positively?

Respond with just a number between 0-10."""

            response = await self.gemini_service.analyze_gemini(prompt)
            if response:
                # Extract numeric score
                import re
                score_match = re.search(r'\b([0-9](?:\.[0-9])?|10(?:\.0)?)\b', response)
                if score_match:
                    return float(score_match.group(1))
                    
        except Exception as e:
            logger.error(f"AI resolution assessment failed: {e}")
            
        return None

    async def _ai_assess_empathy(self, agent_messages: List[Message]) -> Optional[float]:
        """Use AI to assess agent empathy level"""
        try:
            agent_content = "\n".join([msg.message_content for msg in agent_messages])
            
            prompt = f"""Analyze these agent messages for empathy and emotional intelligence.

Agent Messages:
{agent_content}

Rate the empathy level on a scale of 0-10, considering:
- Use of understanding and caring language
- Acknowledgment of customer emotions
- Personal touch and connection
- Professional warmth

Respond with just a number between 0-10."""

            response = await self.gemini_service.analyze_gemini(prompt)
            if response:
                import re
                score_match = re.search(r'\b([0-9](?:\.[0-9])?|10(?:\.0)?)\b', response)
                if score_match:
                    return float(score_match.group(1))
                    
        except Exception as e:
            logger.error(f"AI empathy assessment failed: {e}")
            
        return None

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