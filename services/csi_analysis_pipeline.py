"""
Complete CSI Analysis Pipeline Integration

This service integrates AI-enhanced interaction detection with comprehensive
analytics to provide end-to-end customer service intelligence analysis.

Features:
- End-to-end conversation processing pipeline
- AI-enhanced interaction detection → CSI analytics → insights generation
- Comprehensive reporting and monitoring
- Scalable batch processing for large conversation datasets
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from models import Conversation, InteractionAnalysis, Job, JobMetric
from services.interaction_detection_service import InteractionDetectionService
from services.interaction_analytics_service import InteractionAnalyticsService, AnalyticsReport
from services.gemini_service import GeminiService
import config

logger = logging.getLogger(__name__)

@dataclass
class PipelineResult:
    """Result of complete CSI analysis pipeline"""
    conversation_id: int
    interactions_detected: int
    interactions_analyzed: int
    avg_csi_score: float
    processing_time_seconds: float
    token_usage: int
    errors: List[str]
    success: bool

@dataclass
class BatchResult:
    """Result of batch processing multiple conversations"""
    total_conversations: int
    successful_conversations: int
    total_interactions: int
    avg_csi_score: float
    total_processing_time: float
    total_tokens: int
    errors: List[str]
    detailed_results: List[PipelineResult]

class CSIAnalysisPipeline:
    """
    Complete end-to-end CSI analysis pipeline integrating interaction detection
    and analytics for comprehensive customer service intelligence.
    """
    
    def __init__(self, db: Session):
        """Initialize pipeline with database session and services"""
        self.db = db
        
        # Initialize services
        settings = config.Settings()
        self.gemini_service = GeminiService(api_key=settings.GEMINI_API_KEY)
        self.detection_service = InteractionDetectionService(self.gemini_service)
        self.analytics_service = InteractionAnalyticsService(self.gemini_service)
        
        # Pipeline configuration
        self.enable_ai_enhancement = True
        self.batch_size = 10
        self.max_concurrent = 3
    
    async def process_conversation(self, conversation_id: int) -> PipelineResult:
        """
        Process a single conversation through the complete CSI analysis pipeline.
        
        Args:
            conversation_id: ID of conversation to process
            
        Returns:
            PipelineResult with processing details and metrics
        """
        start_time = datetime.now()
        errors = []
        token_usage = 0
        
        try:
            logger.info(f"Starting CSI pipeline for conversation {conversation_id}")
            
            # Get conversation
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                error_msg = f"Conversation {conversation_id} not found"
                logger.error(error_msg)
                return PipelineResult(
                    conversation_id=conversation_id,
                    interactions_detected=0,
                    interactions_analyzed=0,
                    avg_csi_score=0.0,
                    processing_time_seconds=0.0,
                    token_usage=0,
                    errors=[error_msg],
                    success=False
                )
            
            # Step 1: Detect interactions using AI enhancement
            logger.info(f"Detecting interactions for conversation {conversation_id}")
            detected_interactions = await self.detection_service.detect_interactions(conversation)
            
            # Convert detected interactions to stored InteractionAnalysis records
            interactions = []
            for i, detected in enumerate(detected_interactions):
                # Create InteractionAnalysis record from DetectedInteraction
                interaction = InteractionAnalysis(
                    conversation_id=conversation.id,
                    start_message_id=detected.messages[0].id if detected.messages else 0,
                    end_message_id=detected.messages[-1].id if detected.messages else 0,
                    interaction_start=detected.start_time,
                    interaction_end=detected.end_time,
                    message_count=len(detected.messages),
                    turns_count=len(detected.messages) // 2,  # Estimate conversation turns
                    interaction_duration=(detected.end_time - detected.start_time).total_seconds() / 60.0,  # minutes
                    boundary_method=','.join([method.value for method in detected.detection_methods]),
                    boundary_confidence=detected.confidence,
                    # Set some default timing metrics
                    first_response_time=300.0,  # 5 minutes default
                    avg_response_time=600.0,    # 10 minutes default
                    total_handling_time=(detected.end_time - detected.start_time).total_seconds() / 60.0
                )
                self.db.add(interaction)
                self.db.commit()
                self.db.refresh(interaction)
                interactions.append(interaction)
            
            if not interactions:
                logger.warning(f"No interactions detected for conversation {conversation_id}")
                processing_time = (datetime.now() - start_time).total_seconds()
                return PipelineResult(
                    conversation_id=conversation_id,
                    interactions_detected=0,
                    interactions_analyzed=0,
                    avg_csi_score=0.0,
                    processing_time_seconds=processing_time,
                    token_usage=0,
                    errors=["No interactions detected"],
                    success=True  # Not an error, just no interactions
                )
            
            logger.info(f"Detected {len(interactions)} interactions for conversation {conversation_id}")
            
            # Step 2: Analyze each interaction for CSI metrics
            analyzed_count = 0
            csi_scores = []
            
            for interaction in interactions:
                try:
                    logger.info(f"Analyzing interaction {interaction.id} for CSI metrics")
                    metrics = await self.analytics_service.analyze_interaction(self.db, interaction)
                    
                    if metrics.overall_csi > 0:
                        csi_scores.append(metrics.overall_csi)
                        analyzed_count += 1
                        
                        # Track token usage (estimated from AI calls)
                        if hasattr(metrics, 'token_usage'):
                            token_usage += getattr(metrics, 'token_usage', 0)
                    
                    logger.info(f"Interaction {interaction.id} CSI: {metrics.overall_csi:.2f}")
                    
                except Exception as e:
                    error_msg = f"Error analyzing interaction {interaction.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Calculate results
            avg_csi = sum(csi_scores) / len(csi_scores) if csi_scores else 0.0
            processing_time = (datetime.now() - start_time).total_seconds()
            success = analyzed_count > 0
            
            logger.info(f"Pipeline completed for conversation {conversation_id}: "
                       f"{len(interactions)} interactions, {analyzed_count} analyzed, "
                       f"avg CSI: {avg_csi:.2f}")
            
            return PipelineResult(
                conversation_id=conversation_id,
                interactions_detected=len(interactions),
                interactions_analyzed=analyzed_count,
                avg_csi_score=avg_csi,
                processing_time_seconds=processing_time,
                token_usage=token_usage,
                errors=errors,
                success=success
            )
            
        except Exception as e:
            error_msg = f"Pipeline failed for conversation {conversation_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            processing_time = (datetime.now() - start_time).total_seconds()
            return PipelineResult(
                conversation_id=conversation_id,
                interactions_detected=0,
                interactions_analyzed=0,
                avg_csi_score=0.0,
                processing_time_seconds=processing_time,
                token_usage=0,
                errors=[error_msg],
                success=False
            )
    
    async def _process_conversation_with_interactions(self, conversation_id: int, detected_interactions: List) -> PipelineResult:
        """
        Process a conversation with pre-detected interactions from batch processing.
        
        Args:
            conversation_id: ID of conversation
            detected_interactions: Pre-detected interactions from batch processing
            
        Returns:
            PipelineResult with processing details and metrics
        """
        start_time = datetime.now()
        errors = []
        token_usage = 0
        
        try:
            logger.info(f"Processing conversation {conversation_id} with {len(detected_interactions)} pre-detected interactions")
            
            # Convert detected interactions to stored InteractionAnalysis records
            interactions = []
            for detected in detected_interactions:
                interaction = InteractionAnalysis(
                    conversation_id=conversation_id,
                    start_message_id=detected.messages[0].id if detected.messages else 0,
                    end_message_id=detected.messages[-1].id if detected.messages else 0,
                    interaction_start=detected.start_time,
                    interaction_end=detected.end_time,
                    message_count=len(detected.messages),
                    turns_count=len(detected.messages) // 2,
                    interaction_duration=(detected.end_time - detected.start_time).total_seconds() / 60.0,
                    boundary_method=','.join([method.value for method in detected.detection_methods]),
                    boundary_confidence=detected.confidence,
                    created_at=datetime.utcnow()
                )
                self.db.add(interaction)
                interactions.append(interaction)
            
            self.db.commit()
            for interaction in interactions:
                self.db.refresh(interaction)
            
            # Step 2: Analyze interactions for CSI metrics
            csi_scores = []
            analyzed_count = 0
            
            for interaction in interactions:
                try:
                    logger.info(f"Analyzing interaction {interaction.id} for CSI metrics")
                    metrics = await self.analytics_service.analyze_interaction(self.db, interaction)
                    
                    if metrics.overall_csi > 0:
                        csi_scores.append(metrics.overall_csi)
                        analyzed_count += 1
                        
                        # Track token usage (estimated)
                        if hasattr(metrics, 'token_usage'):
                            token_usage += getattr(metrics, 'token_usage', 0)
                    
                    logger.info(f"Interaction {interaction.id} CSI: {metrics.overall_csi:.2f}")
                    
                except Exception as e:
                    error_msg = f"Error analyzing interaction {interaction.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Calculate results
            avg_csi = sum(csi_scores) / len(csi_scores) if csi_scores else 0.0
            processing_time = (datetime.now() - start_time).total_seconds()
            success = analyzed_count > 0
            
            logger.info(f"Pre-detected pipeline completed for conversation {conversation_id}: "
                       f"{len(interactions)} interactions, {analyzed_count} analyzed, "
                       f"avg CSI: {avg_csi:.2f}")
            
            return PipelineResult(
                conversation_id=conversation_id,
                interactions_detected=len(interactions),
                interactions_analyzed=analyzed_count,
                avg_csi_score=avg_csi,
                processing_time_seconds=processing_time,
                token_usage=token_usage,
                errors=errors,
                success=success
            )
            
        except Exception as e:
            error_msg = f"Pipeline error for conversation {conversation_id}: {str(e)}"
            logger.error(error_msg)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return PipelineResult(
                conversation_id=conversation_id,
                interactions_detected=0,
                interactions_analyzed=0,
                avg_csi_score=0.0,
                processing_time_seconds=processing_time,
                token_usage=token_usage,
                errors=[error_msg],
                success=False
            )
    
    async def process_batch(self, conversation_ids: List[int]) -> BatchResult:
        """
        Process multiple conversations in batch with concurrency control.
        
        Args:
            conversation_ids: List of conversation IDs to process
            
        Returns:
            BatchResult with aggregated processing results
        """
        start_time = datetime.now()
        logger.info(f"Starting batch processing of {len(conversation_ids)} conversations")
        
        # Optimize: Use batch AI processing for better efficiency
        try:
            # Get all conversations
            conversations = []
            for conv_id in conversation_ids:
                conversation = self.db.query(Conversation).filter(Conversation.id == conv_id).first()
                if conversation:
                    conversations.append(conversation)
                else:
                    logger.warning(f"Conversation {conv_id} not found")
            
            # Batch interaction detection (single AI call for all conversations)  
            logger.info(f"Using batch AI enhancement for {len(conversations)} conversations")
            batch_interactions = await self.detection_service.detect_interactions_batch(conversations)
            
            # Process each conversation's detected interactions
            results = []
            for conv_id in conversation_ids:
                if conv_id in batch_interactions:
                    result = await self._process_conversation_with_interactions(
                        conv_id, batch_interactions[conv_id]
                    )
                    results.append(result)
                else:
                    # Create failed result for missing conversation
                    error_msg = f"Conversation {conv_id} not found or failed processing"
                    results.append(PipelineResult(
                        conversation_id=conv_id,
                        interactions_detected=0,
                        interactions_analyzed=0,
                        avg_csi_score=0.0,
                        processing_time_seconds=0.0,
                        token_usage=0,
                        errors=[error_msg],
                        success=False
                    ))
            
        except Exception as e:
            logger.error(f"Batch processing failed, falling back to individual processing: {e}")
            # Fallback: Process conversations individually with concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def process_with_semaphore(conv_id: int) -> PipelineResult:
                async with semaphore:
                    return await self.process_conversation(conv_id)
            
            # Execute batch processing
            tasks = [process_with_semaphore(conv_id) for conv_id in conversation_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        detailed_results = []
        successful_count = 0
        total_interactions = 0
        all_csi_scores = []
        total_tokens = 0
        all_errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = f"Exception processing conversation {conversation_ids[i]}: {str(result)}"
                logger.error(error_msg)
                all_errors.append(error_msg)
                # Create failed result
                detailed_results.append(PipelineResult(
                    conversation_id=conversation_ids[i],
                    interactions_detected=0,
                    interactions_analyzed=0,
                    avg_csi_score=0.0,
                    processing_time_seconds=0.0,
                    token_usage=0,
                    errors=[error_msg],
                    success=False
                ))
            else:
                detailed_results.append(result)
                if result.success:
                    successful_count += 1
                    total_interactions += result.interactions_analyzed
                    if result.avg_csi_score > 0:
                        all_csi_scores.append(result.avg_csi_score)
                    total_tokens += result.token_usage
                
                all_errors.extend(result.errors)
        
        # Calculate aggregated metrics
        avg_csi = sum(all_csi_scores) / len(all_csi_scores) if all_csi_scores else 0.0
        total_processing_time = (datetime.now() - start_time).total_seconds()
        
        batch_result = BatchResult(
            total_conversations=len(conversation_ids),
            successful_conversations=successful_count,
            total_interactions=total_interactions,
            avg_csi_score=avg_csi,
            total_processing_time=total_processing_time,
            total_tokens=total_tokens,
            errors=all_errors,
            detailed_results=detailed_results
        )
        
        logger.info(f"Batch processing completed: {successful_count}/{len(conversation_ids)} successful, "
                   f"avg CSI: {avg_csi:.2f}, {total_interactions} interactions analyzed")
        
        return batch_result
    
    async def generate_comprehensive_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Generate comprehensive CSI analysis report for a time period.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Comprehensive report with analytics, trends, and recommendations
        """
        try:
            logger.info(f"Generating comprehensive report for {start_date} to {end_date}")
            
            # Generate analytics report
            analytics_report = await self.analytics_service.generate_period_report(
                self.db, start_date, end_date
            )
            
            # Get interactions in period for additional analysis
            interactions = self.db.query(InteractionAnalysis).filter(
                and_(
                    InteractionAnalysis.interaction_start >= start_date,
                    InteractionAnalysis.interaction_end <= end_date
                )
            ).all()
            
            # AI enhancement analysis
            ai_enhanced_count = sum(1 for i in interactions if 'ai' in (i.boundary_method or '').lower())
            ai_usage_rate = ai_enhanced_count / len(interactions) if interactions else 0.0
            
            # Detection method breakdown
            method_counts = {}
            for interaction in interactions:
                method = interaction.boundary_method or 'unknown'
                method_counts[method] = method_counts.get(method, 0) + 1
            
            # Quality indicators
            high_confidence_interactions = sum(1 for i in interactions 
                                             if i.boundary_confidence and i.boundary_confidence >= 0.8)
            confidence_rate = high_confidence_interactions / len(interactions) if interactions else 0.0
            
            # Pipeline performance metrics
            pipeline_metrics = {
                'detection_methods': method_counts,
                'ai_enhancement_usage': ai_usage_rate,
                'high_confidence_rate': confidence_rate,
                'avg_interaction_duration': analytics_report.insights.avg_duration,
                'total_processing_volume': len(interactions)
            }
            
            # Combine all analysis
            comprehensive_report = {
                'report_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'analysis_version': '1.0',
                    'pipeline_version': 'ai_enhanced'
                },
                'executive_summary': {
                    'total_interactions': analytics_report.total_interactions,
                    'avg_csi_score': analytics_report.avg_csi_score,
                    'resolution_rate': analytics_report.insights.resolution_rate,
                    'ai_enhancement_rate': ai_usage_rate,
                    'key_insight': self._generate_key_insight(analytics_report)
                },
                'csi_analysis': {
                    'overall_score': analytics_report.avg_csi_score,
                    'pillar_scores': {
                        'effectiveness': analytics_report.metrics.effectiveness_score,
                        'effort': analytics_report.metrics.effort_score,
                        'efficiency': analytics_report.metrics.efficiency_score,
                        'empathy': analytics_report.metrics.empathy_score
                    },
                    'trends': analytics_report.trends,
                    'benchmarks': analytics_report.benchmarks
                },
                'operational_insights': {
                    'interactions_overview': analytics_report.insights.__dict__,
                    'pipeline_performance': pipeline_metrics,
                    'quality_indicators': {
                        'high_confidence_rate': confidence_rate,
                        'ai_enhancement_usage': ai_usage_rate,
                        'detection_accuracy': self._estimate_detection_accuracy(interactions)
                    }
                },
                'alerts_and_recommendations': {
                    'performance_alerts': analytics_report.alerts,
                    'strategic_recommendations': analytics_report.insights.recommendations,
                    'technical_recommendations': self._generate_technical_recommendations(pipeline_metrics)
                },
                'detailed_analytics': analytics_report.__dict__
            }
            
            logger.info(f"Generated comprehensive report with {len(interactions)} interactions analyzed")
            return comprehensive_report
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return {
                'error': str(e),
                'report_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'status': 'failed'
                }
            }
    
    def _generate_key_insight(self, report: AnalyticsReport) -> str:
        """Generate key insight for executive summary"""
        if report.avg_csi_score >= 8.0:
            return f"Excellent service quality with {report.avg_csi_score:.1f}/10 CSI score"
        elif report.avg_csi_score >= 7.0:
            return f"Good service quality with room for improvement ({report.avg_csi_score:.1f}/10)"
        elif report.avg_csi_score >= 6.0:
            return f"Moderate service quality requiring attention ({report.avg_csi_score:.1f}/10)"
        else:
            return f"Service quality below expectations ({report.avg_csi_score:.1f}/10) - immediate action needed"
    
    def _estimate_detection_accuracy(self, interactions: List[InteractionAnalysis]) -> float:
        """Estimate detection accuracy based on confidence scores"""
        if not interactions:
            return 0.0
        
        confidence_scores = [i.boundary_confidence for i in interactions 
                           if i.boundary_confidence is not None]
        
        if not confidence_scores:
            return 0.7  # Default estimate
        
        return sum(confidence_scores) / len(confidence_scores)
    
    def _generate_technical_recommendations(self, pipeline_metrics: Dict[str, Any]) -> List[str]:
        """Generate technical recommendations based on pipeline performance"""
        recommendations = []
        
        # AI enhancement usage
        ai_usage = pipeline_metrics.get('ai_enhancement_usage', 0.0)
        if ai_usage < 0.5:
            recommendations.append("Increase AI enhancement usage for better boundary detection accuracy")
        elif ai_usage > 0.9:
            recommendations.append("Consider optimizing AI usage to balance accuracy and cost")
        
        # Confidence rates
        confidence_rate = pipeline_metrics.get('high_confidence_rate', 0.0)
        if confidence_rate < 0.7:
            recommendations.append("Review detection rules and AI prompts to improve confidence scores")
        
        # Processing volume
        volume = pipeline_metrics.get('total_processing_volume', 0)
        if volume > 1000:
            recommendations.append("Consider implementing batch processing optimizations for large datasets")
        
        return recommendations
    
    async def process_recent_conversations(self, hours: int = 24) -> BatchResult:
        """Process conversations from the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        conversations = self.db.query(Conversation).filter(
            Conversation.first_message_time >= cutoff_time
        ).limit(50).all()  # Limit for safety
        
        if not conversations:
            logger.info(f"No conversations found in the last {hours} hours")
            return BatchResult(
                total_conversations=0,
                successful_conversations=0,
                total_interactions=0,
                avg_csi_score=0.0,
                total_processing_time=0.0,
                total_tokens=0,
                errors=[],
                detailed_results=[]
            )
        
        conversation_ids = [c.id for c in conversations]
        logger.info(f"Processing {len(conversation_ids)} recent conversations")
        
        return await self.process_batch(conversation_ids)
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and health metrics"""
        try:
            # Recent processing stats
            recent_interactions = self.db.query(InteractionAnalysis).filter(
                InteractionAnalysis.created_at >= datetime.now() - timedelta(hours=24)
            ).all()
            
            # AI enhancement stats
            ai_enhanced = sum(1 for i in recent_interactions 
                            if 'ai' in (i.boundary_method or '').lower())
            
            # Quality metrics
            high_confidence = sum(1 for i in recent_interactions 
                                if i.boundary_confidence and i.boundary_confidence >= 0.8)
            
            status = {
                'pipeline_health': 'healthy' if len(recent_interactions) > 0 else 'idle',
                'last_24h_interactions': len(recent_interactions),
                'ai_enhancement_rate': ai_enhanced / len(recent_interactions) if recent_interactions else 0.0,
                'high_confidence_rate': high_confidence / len(recent_interactions) if recent_interactions else 0.0,
                'services_status': {
                    'detection_service': 'active',
                    'analytics_service': 'active',
                    'gemini_service': 'active'
                },
                'configuration': {
                    'ai_enhancement_enabled': self.enable_ai_enhancement,
                    'batch_size': self.batch_size,
                    'max_concurrent': self.max_concurrent
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            return {
                'pipeline_health': 'error',
                'error': str(e),
                'services_status': {
                    'detection_service': 'unknown',
                    'analytics_service': 'unknown', 
                    'gemini_service': 'unknown'
                }
            }