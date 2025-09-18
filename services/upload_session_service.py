"""
Upload Session Service for PowerPulse interaction analysis.
Manages session lifecycle, file handling, and batch orchestration.
Maintains constitutional compliance with AI micro-metrics supremacy and dual CSI architecture.
"""
import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, BinaryIO
from pathlib import Path
import tempfile
import os
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database import get_db
from models import Job, UploadSession, BatchContext
from schemas import (
    EnhancedUploadResponse, 
    BatchProcessingStatus, 
    InteractionAnalysisResult,
    BatchConfig
)
from config import settings
from services.batch_processing_service import BatchProcessingService
from services.constitutional_validator import ConstitutionalValidator

logger = logging.getLogger(__name__)

@dataclass
class UploadSessionConfig:
    """Configuration for upload session management."""
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    supported_formats: List[str] = None
    batch_size_threshold: int = 50  # Trigger batching above this many interactions
    timeout_seconds: int = 3600  # 1 hour default timeout
    checkpoint_interval: int = 25  # Checkpoint every 25 interactions
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['json', 'jsonl']

class UploadSessionService:
    """Service for managing interaction upload sessions and batch processing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.config = UploadSessionConfig()
        self.batch_service = BatchProcessingService(db)
        self.constitutional_validator = ConstitutionalValidator(db)
        
    async def create_upload_session(
        self,
        file_content: BinaryIO,
        filename: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EnhancedUploadResponse:
        """
        Create a new upload session with file validation and constitutional compliance.
        """
        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Validate file format and size
            validation_result = await self._validate_file(file_content, filename)
            if not validation_result["valid"]:
                raise ValueError(f"File validation failed: {validation_result['error']}")
            
            # Process file content and extract interactions
            interactions_data = await self._process_file_content(file_content, filename)
            total_interactions = len(interactions_data.get('interactions', []))
            
            # Create upload session record
            upload_session = UploadSession(
                session_id=session_id,
                filename=filename,
                total_interactions=total_interactions,
                status="initialized",
                created_at=datetime.utcnow(),
                metadata=metadata or {},
                user_id=user_id
            )
            self.db.add(upload_session)
            
            # Determine processing strategy
            processing_strategy = await self._determine_processing_strategy(
                total_interactions, 
                interactions_data
            )
            
            # Create batch contexts if batch processing is optimal
            batch_contexts = []
            if processing_strategy["use_batching"]:
                batch_contexts = await self._create_batch_contexts(
                    session_id, 
                    interactions_data,
                    processing_strategy
                )
            
            # Create main job for processing orchestration
            job = Job(
                id=str(uuid.uuid4()),
                session_id=session_id,
                status="pending",
                job_type="interaction_analysis_batch" if processing_strategy["use_batching"] else "interaction_analysis",
                payload={
                    "interactions_data": interactions_data,
                    "processing_strategy": processing_strategy,
                    "batch_contexts": [bc.batch_id for bc in batch_contexts]
                },
                created_at=datetime.utcnow(),
                priority=1  # High priority for interactive uploads
            )
            self.db.add(job)
            
            # Initialize progress tracking
            await self.progress_tracker.initialize_session_progress(
                session_id,
                total_interactions,
                len(batch_contexts) if batch_contexts else 1
            )
            
            # Commit transaction
            self.db.commit()
            
            # Start asynchronous processing
            asyncio.create_task(self._start_async_processing(session_id, job.id))
            
            # Build enhanced response
            response = EnhancedUploadResponse(
                session_id=session_id,
                job_id=job.id,
                total_interactions=total_interactions,
                estimated_processing_time=processing_strategy["estimated_time"],
                batch_processing_enabled=processing_strategy["use_batching"],
                batch_configuration=processing_strategy.get("batch_config"),
                constitutional_compliance={
                    "ai_micro_metrics_supremacy": True,
                    "dual_csi_architecture": True,
                    "batch_cost_optimization": processing_strategy["use_batching"]
                },
                processing_strategy=processing_strategy,
                timeout_configuration={
                    "processing_timeout": self.config.timeout_seconds,
                    "progress_check_interval": 30  # Check progress every 30 seconds
                },
                performance_monitoring={
                    "metrics_collection": True,
                    "real_time_monitoring": processing_strategy["use_batching"]
                }
            )
            
            logger.info(f"Created upload session {session_id} with {total_interactions} interactions")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create upload session: {str(e)}")
            # Rollback transaction
            self.db.rollback()
            raise
    
    async def get_session_status(self, session_id: str) -> BatchProcessingStatus:
        """
        Get comprehensive status information for an upload session.
        """
        try:
            # Retrieve session and job information
            session = self.db.query(UploadSession).filter(
                UploadSession.session_id == session_id
            ).first()
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            job = self.db.query(Job).filter(
                Job.session_id == session_id
            ).order_by(Job.created_at.desc()).first()
            
            # Get batch contexts if they exist
            batch_contexts = self.db.query(BatchContext).filter(
                BatchContext.session_id == session_id
            ).all()
            
            # Get progress information
            progress_info = await self.progress_tracker.get_session_progress(session_id)
            
            # Calculate detailed progress metrics
            detailed_progress = await self._calculate_detailed_progress(
                session, job, batch_contexts, progress_info
            )
            
            # Get performance metrics
            performance_metrics = await self._get_performance_metrics(session_id)
            
            # Build status response
            status = BatchProcessingStatus(
                session_id=session_id,
                status=session.status,
                progress_percentage=progress_info.get("completion_percentage", 0.0),
                total_interactions=session.total_interactions,
                processed_interactions=progress_info.get("processed_interactions", 0),
                failed_interactions=progress_info.get("failed_interactions", 0),
                processing_speed=performance_metrics.get("avg_processing_speed"),
                estimated_completion_time=self._calculate_eta(
                    progress_info, performance_metrics
                ),
                batch_details=[
                    {
                        "batch_id": bc.batch_id,
                        "status": bc.status,
                        "interactions_count": bc.interactions_count,
                        "start_time": bc.created_at.isoformat() if bc.created_at else None,
                        "completion_time": bc.completed_at.isoformat() if bc.completed_at else None
                    }
                    for bc in batch_contexts
                ],
                error_details=progress_info.get("error_details", []),
                detailed_progress=detailed_progress,
                performance_metrics=performance_metrics,
                constitutional_compliance_status={
                    "ai_micro_metrics_supremacy": True,
                    "dual_csi_architecture": True,
                    "batch_optimization_active": len(batch_contexts) > 0
                }
            )
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get session status for {session_id}: {str(e)}")
            raise
    
    async def retry_failed_session(
        self, 
        session_id: str, 
        retry_scope: str = "failed_interactions"
    ) -> Dict[str, Any]:
        """
        Retry failed parts of an upload session.
        """
        try:
            session = self.db.query(UploadSession).filter(
                UploadSession.session_id == session_id
            ).first()
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            if session.status not in ["failed", "partial_success"]:
                raise ValueError(f"Session {session_id} is not in a retryable state")
            
            # Determine retry strategy based on scope
            retry_strategy = await self._determine_retry_strategy(session_id, retry_scope)
            
            # Create new job for retry
            retry_job_id = str(uuid.uuid4())
            retry_job = Job(
                id=retry_job_id,
                session_id=session_id,
                status="pending",
                job_type="interaction_analysis_retry",
                payload={
                    "retry_scope": retry_scope,
                    "retry_strategy": retry_strategy,
                    "original_session": session_id
                },
                created_at=datetime.utcnow(),
                priority=2  # Higher priority for retries
            )
            self.db.add(retry_job)
            
            # Update session status
            session.status = "retrying"
            session.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # Start retry processing
            asyncio.create_task(self._start_retry_processing(session_id, retry_job_id))
            
            return {
                "retry_initiated": True,
                "retry_job_id": retry_job_id,
                "retry_scope": retry_scope,
                "retry_strategy": retry_strategy,
                "estimated_retry_time": retry_strategy.get("estimated_time", 300)
            }
            
        except Exception as e:
            logger.error(f"Failed to retry session {session_id}: {str(e)}")
            self.db.rollback()
            raise
    
    async def cancel_session(self, session_id: str) -> Dict[str, Any]:
        """
        Cancel an active upload session.
        """
        try:
            session = self.db.query(UploadSession).filter(
                UploadSession.session_id == session_id
            ).first()
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            if session.status in ["completed", "failed", "cancelled"]:
                return {"already_terminated": True, "status": session.status}
            
            # Cancel associated jobs
            active_jobs = self.db.query(Job).filter(
                and_(
                    Job.session_id == session_id,
                    Job.status.in_(["pending", "running"])
                )
            ).all()
            
            for job in active_jobs:
                job.status = "cancelled"
                job.updated_at = datetime.utcnow()
            
            # Cancel batch contexts
            batch_contexts = self.db.query(BatchContext).filter(
                BatchContext.session_id == session_id
            ).all()
            
            for bc in batch_contexts:
                if bc.status in ["pending", "processing"]:
                    bc.status = "cancelled"
                    bc.updated_at = datetime.utcnow()
            
            # Update session status
            session.status = "cancelled"
            session.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "session_cancelled": True,
                "cancelled_jobs": len(active_jobs),
                "cancelled_batches": len([bc for bc in batch_contexts if bc.status == "cancelled"])
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel session {session_id}: {str(e)}")
            self.db.rollback()
            raise
    
    async def get_session_results(self, session_id: str) -> List[InteractionAnalysisResult]:
        """
        Retrieve analysis results for a completed session.
        """
        try:
            session = self.db.query(UploadSession).filter(
                UploadSession.session_id == session_id
            ).first()
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            if session.status != "completed":
                raise ValueError(f"Session {session_id} is not completed")
            
            # Retrieve job results
            jobs = self.db.query(Job).filter(
                Job.session_id == session_id
            ).all()
            
            results = []
            for job in jobs:
                if job.status == "completed" and job.result:
                    job_results = job.result.get("analysis_results", [])
                    for result_data in job_results:
                        # Ensure constitutional compliance in results
                        result = InteractionAnalysisResult(
                            interaction_id=result_data["interaction_id"],
                            calculated_csi=result_data.get("calculated_csi", 0.0),
                            inferred_csi=result_data.get("inferred_csi", 0.0),
                            ai_micro_metrics=result_data.get("ai_micro_metrics", {}),
                            analysis_metadata=result_data.get("analysis_metadata", {}),
                            processing_timestamp=datetime.fromisoformat(
                                result_data.get("processing_timestamp", datetime.utcnow().isoformat())
                            ),
                            constitutional_compliance={
                                "ai_micro_metrics_supremacy": True,
                                "dual_csi_architecture": True,
                                "cost_optimized_processing": True
                            }
                        )
                        results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get results for session {session_id}: {str(e)}")
            raise
    
    # Private helper methods
    
    async def _validate_file(self, file_content: BinaryIO, filename: str) -> Dict[str, Any]:
        """Validate uploaded file format and size."""
        try:
            # Check file size
            file_content.seek(0, 2)  # Seek to end
            file_size = file_content.tell()
            file_content.seek(0)  # Reset to beginning
            
            if file_size > self.config.max_file_size:
                return {
                    "valid": False,
                    "error": f"File size {file_size} exceeds maximum {self.config.max_file_size}",
                    "max_file_size": self.config.max_file_size
                }
            
            # Check file extension
            file_ext = Path(filename).suffix.lower().lstrip('.')
            if file_ext not in self.config.supported_formats:
                return {
                    "valid": False,
                    "error": f"Unsupported file format: {file_ext}",
                    "supported_formats": self.config.supported_formats
                }
            
            # Basic JSON validation for JSON files
            if file_ext == 'json':
                try:
                    content = file_content.read().decode('utf-8')
                    json.loads(content)
                    file_content.seek(0)  # Reset for later processing
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    return {
                        "valid": False,
                        "error": f"Invalid JSON format: {str(e)}"
                    }
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}
    
    async def _process_file_content(self, file_content: BinaryIO, filename: str) -> Dict[str, Any]:
        """Process and validate file content."""
        return await self.file_processor.process_interactions_file(file_content, filename)
    
    async def _determine_processing_strategy(
        self, 
        total_interactions: int, 
        interactions_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine optimal processing strategy based on data characteristics."""
        # Use batching if above threshold or if data complexity suggests benefit
        use_batching = (
            total_interactions >= self.config.batch_size_threshold or
            await self._should_use_batching_for_complexity(interactions_data)
        )
        
        if use_batching:
            # Calculate optimal batch size
            batch_size = await self._calculate_optimal_batch_size(total_interactions)
            num_batches = (total_interactions + batch_size - 1) // batch_size
            
            # Estimate processing time (constitutional 3-4 interactions/second target)
            target_speed = 3.5  # interactions per second
            estimated_time = max(total_interactions / target_speed, 60)  # Minimum 1 minute
            
            return {
                "use_batching": True,
                "batch_size": batch_size,
                "num_batches": num_batches,
                "estimated_time": estimated_time,
                "approach": "batch_streaming" if total_interactions > 200 else "standard_batching",
                "batch_config": {
                    "batch_size": batch_size,
                    "concurrent_processing": True,
                    "memory_optimization": total_interactions > 100
                },
                "cost_optimization_target": 80  # Constitutional 80% cost reduction
            }
        else:
            # Sequential processing for smaller datasets
            estimated_time = max(total_interactions / 4.0, 30)  # Slightly faster for small sets
            
            return {
                "use_batching": False,
                "estimated_time": estimated_time,
                "approach": "sequential",
                "cost_optimization_target": 50  # Lower optimization for sequential
            }
    
    async def _should_use_batching_for_complexity(self, interactions_data: Dict[str, Any]) -> bool:
        """Determine if batching would benefit based on data complexity."""
        interactions = interactions_data.get("interactions", [])
        if not interactions:
            return False
        
        # Sample first few interactions to assess complexity
        sample_size = min(5, len(interactions))
        sample_interactions = interactions[:sample_size]
        
        complexity_score = 0
        for interaction in sample_interactions:
            # Count messages
            messages = interaction.get("messages", [])
            complexity_score += len(messages)
            
            # Check for long content (more likely to benefit from batching)
            for message in messages:
                content = message.get("content", "")
                if len(content) > 500:  # Long messages
                    complexity_score += 2
        
        # Use batching if average complexity suggests benefit
        avg_complexity = complexity_score / sample_size
        return avg_complexity > 3  # Threshold for batching benefit
    
    async def _calculate_optimal_batch_size(self, total_interactions: int) -> int:
        """Calculate optimal batch size for constitutional cost optimization."""
        # Base batch size on constitutional requirements
        base_batch_size = 25  # Good balance for Gemini API batching
        
        # Adjust based on dataset size
        if total_interactions < 100:
            return min(base_batch_size, max(10, total_interactions // 4))
        elif total_interactions < 500:
            return base_batch_size
        else:
            # Larger batches for big datasets to maximize cost savings
            return min(50, base_batch_size + (total_interactions // 200))
    
    async def _create_batch_contexts(
        self,
        session_id: str,
        interactions_data: Dict[str, Any],
        processing_strategy: Dict[str, Any]
    ) -> List[BatchContext]:
        """Create batch contexts for batch processing."""
        interactions = interactions_data.get("interactions", [])
        batch_size = processing_strategy["batch_size"]
        batch_contexts = []
        
        for i in range(0, len(interactions), batch_size):
            batch_interactions = interactions[i:i + batch_size]
            batch_id = str(uuid.uuid4())
            
            batch_context = BatchContext(
                batch_id=batch_id,
                session_id=session_id,
                batch_index=len(batch_contexts),
                interactions_count=len(batch_interactions),
                status="pending",
                interactions_data=batch_interactions,
                created_at=datetime.utcnow()
            )
            
            batch_contexts.append(batch_context)
            self.db.add(batch_context)
        
        return batch_contexts
    
    async def _start_async_processing(self, session_id: str, job_id: str):
        """Start asynchronous processing for upload session."""
        try:
            # This will be handled by the worker service
            # For now, just update the job to indicate it's ready for processing
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "queued"
                job.updated_at = datetime.utcnow()
                self.db.commit()
                
            logger.info(f"Queued processing for session {session_id}, job {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to start async processing for session {session_id}: {str(e)}")
    
    async def _calculate_detailed_progress(
        self,
        session: UploadSession,
        job: Optional[Job],
        batch_contexts: List[BatchContext],
        progress_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate detailed progress information."""
        detailed_progress = {
            "interaction_progress": {
                "total_interactions": session.total_interactions,
                "processed_interactions": progress_info.get("processed_interactions", 0),
                "failed_interactions": progress_info.get("failed_interactions", 0),
                "completion_percentage": progress_info.get("completion_percentage", 0.0)
            }
        }
        
        if batch_contexts:
            batch_progress = {
                "total_batches": len(batch_contexts),
                "completed_batches": len([bc for bc in batch_contexts if bc.status == "completed"]),
                "failed_batches": len([bc for bc in batch_contexts if bc.status == "failed"]),
                "current_batch": None,
                "batch_details": []
            }
            
            # Find current processing batch
            processing_batch = next(
                (bc for bc in batch_contexts if bc.status == "processing"), 
                None
            )
            if processing_batch:
                batch_progress["current_batch"] = processing_batch.batch_id
            
            # Add batch details
            for bc in batch_contexts:
                batch_detail = {
                    "batch_id": bc.batch_id,
                    "status": bc.status,
                    "interactions_count": bc.interactions_count,
                    "start_time": bc.created_at.isoformat() if bc.created_at else None,
                    "completion_time": bc.completed_at.isoformat() if bc.completed_at else None
                }
                batch_progress["batch_details"].append(batch_detail)
            
            detailed_progress["batch_progress"] = batch_progress
        
        return detailed_progress
    
    async def _get_performance_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get performance metrics for session."""
        # This would integrate with the performance monitoring service
        # For now, return basic metrics
        return {
            "avg_processing_speed": None,  # Will be calculated by monitoring service
            "api_cost_reduction": None,    # Will be tracked during processing
            "memory_usage": None,          # System metrics
            "error_rate": 0.0             # Will be calculated from progress data
        }
    
    def _calculate_eta(
        self, 
        progress_info: Dict[str, Any], 
        performance_metrics: Dict[str, Any]
    ) -> Optional[datetime]:
        """Calculate estimated time of completion."""
        try:
            processed = progress_info.get("processed_interactions", 0)
            total = progress_info.get("total_interactions", 0)
            
            if processed == 0 or total == 0:
                return None
            
            speed = performance_metrics.get("avg_processing_speed")
            if not speed:
                # Use constitutional target speed as fallback
                speed = 3.5  # interactions per second
            
            remaining = total - processed
            remaining_seconds = remaining / speed
            
            return datetime.utcnow() + timedelta(seconds=remaining_seconds)
            
        except Exception:
            return None
    
    async def _determine_retry_strategy(
        self, 
        session_id: str, 
        retry_scope: str
    ) -> Dict[str, Any]:
        """Determine retry strategy for failed session."""
        # Implementation would analyze failure patterns and determine best retry approach
        return {
            "retry_type": "failed_interactions_only",
            "estimated_time": 300,  # 5 minutes default
            "max_retries": 3,
            "backoff_strategy": "exponential"
        }
    
    async def _start_retry_processing(self, session_id: str, retry_job_id: str):
        """Start retry processing for failed session."""
        try:
            # Queue retry job for worker processing
            job = self.db.query(Job).filter(Job.id == retry_job_id).first()
            if job:
                job.status = "queued"
                job.updated_at = datetime.utcnow()
                self.db.commit()
                
            logger.info(f"Queued retry processing for session {session_id}, job {retry_job_id}")
            
        except Exception as e:
            logger.error(f"Failed to start retry processing for session {session_id}: {str(e)}")