"""
Constitutional Validator Service - Ensures AI micro-metrics supremacy and dual CSI compliance.
Part of PowerPulse's constitutional framework for interaction analysis.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from models import UploadSession, BatchContext, Job, DailyAnalysis, InteractionAnalysis
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class ComplianceResult:
    """Result of constitutional compliance validation."""
    is_compliant: bool
    violations: List[str]
    metrics: Dict[str, Any]
    recommendations: List[str]


class ConstitutionalValidator:
    """
    Validates constitutional compliance for PowerPulse system.
    Ensures AI micro-metrics supremacy and dual CSI architecture compliance.
    """
    
    # Constitutional requirements
    MIN_COST_REDUCTION_PERCENTAGE = 80.0
    MAX_PROCESSING_TIME_SECONDS = 300.0  # 5 minutes per session
    REQUIRED_CSI_FIELDS = ['calculated_csi', 'inferred_csi']
    MIN_INTERACTIONS_PER_SECOND = 3.0
    MAX_INTERACTIONS_PER_SECOND = 4.0
    
    async def validate_session_compliance(
        self, 
        session_id: str, 
        db: Session
    ) -> ComplianceResult:
        """
        Validate constitutional compliance for a specific upload session.
        
        Args:
            session_id: Upload session identifier
            db: Database session
            
        Returns:
            ComplianceResult with compliance status and details
        """
        violations = []
        metrics = {}
        recommendations = []
        
        try:
            # Fetch session data
            session = db.get(UploadSession, session_id)
            if not session:
                return ComplianceResult(
                    is_compliant=False,
                    violations=[f"Session {session_id} not found"],
                    metrics={},
                    recommendations=["Verify session exists"]
                )
            
            # 1. Cost reduction compliance (80% minimum)
            cost_saved = session.cost_saved_percentage or 0.0
            metrics['cost_saved_percentage'] = cost_saved
            
            if cost_saved < self.MIN_COST_REDUCTION_PERCENTAGE:
                violations.append(f"Cost reduction {cost_saved}% below required {self.MIN_COST_REDUCTION_PERCENTAGE}%")
                recommendations.append("Optimize batch processing strategy")
            
            # 2. Processing speed compliance (3-4 interactions/second)
            if session.processing_time_seconds and session.interactions_processed:
                interactions_per_second = session.interactions_processed / session.processing_time_seconds
                metrics['interactions_per_second'] = interactions_per_second
                
                if interactions_per_second < self.MIN_INTERACTIONS_PER_SECOND:
                    violations.append(f"Processing speed {interactions_per_second:.2f} below minimum {self.MIN_INTERACTIONS_PER_SECOND} interactions/second")
                    recommendations.append("Increase batch size or optimize processing pipeline")
                elif interactions_per_second > self.MAX_INTERACTIONS_PER_SECOND:
                    violations.append(f"Processing speed {interactions_per_second:.2f} exceeds maximum {self.MAX_INTERACTIONS_PER_SECOND} interactions/second")
                    recommendations.append("Reduce batch size to maintain quality")
            
            # 3. Dual CSI architecture compliance
            csi_compliance = await self._validate_csi_compliance(session_id, db)
            if not csi_compliance['is_compliant']:
                violations.extend(csi_compliance['violations'])
                recommendations.extend(csi_compliance['recommendations'])
            
            metrics.update(csi_compliance['metrics'])
            
            # 4. AI micro-metrics supremacy validation
            ai_metrics_compliance = await self._validate_ai_metrics_supremacy(session_id, db)
            if not ai_metrics_compliance['is_compliant']:
                violations.extend(ai_metrics_compliance['violations'])
                recommendations.extend(ai_metrics_compliance['recommendations'])
            
            metrics.update(ai_metrics_compliance['metrics'])
            
            is_compliant = len(violations) == 0
            
            logger.info(f"Session {session_id} compliance check: {'COMPLIANT' if is_compliant else 'VIOLATIONS DETECTED'}")
            
            return ComplianceResult(
                is_compliant=is_compliant,
                violations=violations,
                metrics=metrics,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error validating session compliance for {session_id}: {e}")
            return ComplianceResult(
                is_compliant=False,
                violations=[f"Validation error: {str(e)}"],
                metrics={},
                recommendations=["Check system logs and retry validation"]
            )
    
    async def validate_system_compliance(self, db: Session) -> ComplianceResult:
        """
        Validate overall system constitutional compliance.
        
        Args:
            db: Database session
            
        Returns:
            ComplianceResult for system-wide compliance
        """
        violations = []
        metrics = {}
        recommendations = []
        
        try:
            # System-wide metrics
            total_sessions = db.query(UploadSession).count()
            completed_sessions = db.query(UploadSession).filter(UploadSession.status == 'completed').count()
            
            metrics['total_sessions'] = total_sessions
            metrics['completed_sessions'] = completed_sessions
            
            if total_sessions > 0:
                success_rate = (completed_sessions / total_sessions) * 100
                metrics['success_rate_percentage'] = success_rate
                
                if success_rate < 95.0:  # Constitutional requirement: 95% success rate
                    violations.append(f"System success rate {success_rate}% below required 95%")
                    recommendations.append("Investigate failed sessions and improve error handling")
            
            # Average cost savings across all sessions
            avg_cost_savings = (
                db.query(func.avg(UploadSession.cost_saved_percentage))
                .filter(UploadSession.status == 'completed')
                .scalar() or 0.0
            )
            
            metrics['average_cost_savings'] = avg_cost_savings
            
            if avg_cost_savings < self.MIN_COST_REDUCTION_PERCENTAGE:
                violations.append(f"Average cost savings {avg_cost_savings}% below constitutional requirement")
                recommendations.append("Review and optimize batch processing strategies system-wide")
            
            # Validate constitutional data integrity
            integrity_check = await self._validate_data_integrity(db)
            if not integrity_check['is_compliant']:
                violations.extend(integrity_check['violations'])
                recommendations.extend(integrity_check['recommendations'])
            
            is_compliant = len(violations) == 0
            
            logger.info(f"System compliance check: {'COMPLIANT' if is_compliant else 'VIOLATIONS DETECTED'}")
            
            return ComplianceResult(
                is_compliant=is_compliant,
                violations=violations,
                metrics=metrics,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error validating system compliance: {e}")
            return ComplianceResult(
                is_compliant=False,
                violations=[f"System validation error: {str(e)}"],
                metrics={},
                recommendations=["Check system health and database connectivity"]
            )
    
    async def _validate_csi_compliance(self, session_id: str, db: Session) -> Dict[str, Any]:
        """Validate dual CSI architecture compliance."""
        try:
            # Check if interactions have both calculated and inferred CSI
            interactions_query = (
                db.query(InteractionAnalysis)
                .join(DailyAnalysis)
                .join(Job)
                .filter(Job.upload_id == session_id)
            )
            
            total_interactions = interactions_query.count()
            
            if total_interactions == 0:
                return {
                    'is_compliant': True,  # No interactions to validate
                    'violations': [],
                    'recommendations': [],
                    'metrics': {'total_interactions': 0}
                }
            
            # Count interactions with missing CSI fields
            missing_calculated_csi = (
                interactions_query
                .filter(InteractionAnalysis.csi_score.is_(None))
                .count()
            )
            
            missing_inferred_csi = (
                interactions_query
                .filter(InteractionAnalysis.csi_score < 0.75)
                .count()
            )
            
            violations = []
            recommendations = []
            
            if missing_calculated_csi > 0:
                violations.append(f"{missing_calculated_csi} interactions missing calculated_csi")
                recommendations.append("Ensure CSI calculation pipeline is functioning")
            
            if missing_inferred_csi > 0:
                violations.append(f"{missing_inferred_csi} interactions missing inferred_csi")
                recommendations.append("Verify AI inference pipeline for CSI generation")
            
            return {
                'is_compliant': len(violations) == 0,
                'violations': violations,
                'recommendations': recommendations,
                'metrics': {
                    'total_interactions': total_interactions,
                    'missing_calculated_csi': missing_calculated_csi,
                    'missing_inferred_csi': missing_inferred_csi,
                    'csi_completeness_percentage': ((total_interactions - max(missing_calculated_csi, missing_inferred_csi)) / total_interactions * 100) if total_interactions > 0 else 100
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating CSI compliance: {e}")
            return {
                'is_compliant': False,
                'violations': [f"CSI validation error: {str(e)}"],
                'recommendations': ["Check CSI pipeline integrity"],
                'metrics': {}
            }
    
    async def _validate_ai_metrics_supremacy(self, session_id: str, db: Session) -> Dict[str, Any]:
        """Validate AI micro-metrics supremacy requirements."""
        try:
            # AI metrics supremacy: AI-generated metrics should be present and accurate
            session = db.get(UploadSession, session_id)
            
            violations = []
            recommendations = []
            metrics = {}
            
            # Check for AI-generated batch insights
            batch_contexts = (
                db.query(BatchContext)
                .filter(BatchContext.session_id == session_id)
                .all()
            )
            
            ai_insights_count = sum(1 for bc in batch_contexts if bc.ai_insights)
            metrics['ai_insights_coverage'] = (ai_insights_count / len(batch_contexts) * 100) if batch_contexts else 0
            
            if metrics['ai_insights_coverage'] < 90.0:  # Constitutional requirement: 90% AI insights coverage
                violations.append(f"AI insights coverage {metrics['ai_insights_coverage']}% below required 90%")
                recommendations.append("Improve AI insight generation in batch processing")
            
            # Validate AI-driven cost optimization
            if session and session.cost_saved_percentage:
                if session.cost_saved_percentage < self.MIN_COST_REDUCTION_PERCENTAGE:
                    violations.append("AI-driven cost optimization below constitutional requirements")
                    recommendations.append("Enhance AI algorithms for better cost optimization")
            
            return {
                'is_compliant': len(violations) == 0,
                'violations': violations,
                'recommendations': recommendations,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Error validating AI metrics supremacy: {e}")
            return {
                'is_compliant': False,
                'violations': [f"AI metrics validation error: {str(e)}"],
                'recommendations': ["Check AI services and metrics collection"],
                'metrics': {}
            }
    
    async def _validate_data_integrity(self, db: Session) -> Dict[str, Any]:
        """Validate constitutional data integrity requirements."""
        try:
            violations = []
            recommendations = []
            
            # Check for orphaned records (constitutional requirement: no data loss)
            orphaned_jobs = (
                db.query(Job)
                .filter(Job.upload_id.notin_(
                    db.query(UploadSession.session_id)
                ))
                .count()
            )
            
            if orphaned_jobs > 0:
                violations.append(f"{orphaned_jobs} orphaned job records found")
                recommendations.append("Clean up orphaned data and improve referential integrity")
            
            # Check for incomplete batch contexts
            incomplete_batches = (
                db.query(BatchContext)
                .filter(BatchContext.status != 'completed')
                .count()
            )
            
            if incomplete_batches > 10:  # Allow some incomplete batches for active processing
                violations.append(f"{incomplete_batches} incomplete batch contexts")
                recommendations.append("Review and complete pending batch processing")
            
            return {
                'is_compliant': len(violations) == 0,
                'violations': violations,
                'recommendations': recommendations,
                'metrics': {
                    'orphaned_jobs': orphaned_jobs,
                    'incomplete_batches': incomplete_batches
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating data integrity: {e}")
            return {
                'is_compliant': False,
                'violations': [f"Data integrity validation error: {str(e)}"],
                'recommendations': ["Check database integrity and constraints"],
                'metrics': {}
            }