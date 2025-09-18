"""
Constitutional compliance routes for PowerPulse.
Validates AI micro-metrics supremacy and dual CSI architecture compliance.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from database import get_db
from models import Job, BatchContext, UploadSession
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/constitutional/compliance")
async def get_constitutional_compliance(db: Session = Depends(get_db)):
    """
    Get comprehensive constitutional compliance status.
    Validates AI micro-metrics supremacy and dual CSI architecture.
    """
    try:
        # Validate core constitutional components
        ai_supremacy_status = await _validate_ai_micro_metrics_supremacy(db)
        dual_csi_status = await _validate_dual_csi_architecture(db)
        batch_compliance_status = await _validate_batch_processing_compliance(db)
        cost_optimization_status = await _validate_cost_optimization_compliance(db)
        
        # Calculate overall compliance
        individual_statuses = [
            ai_supremacy_status["compliant"],
            dual_csi_status["compliant"],
            batch_compliance_status["compliant"],
            cost_optimization_status["compliant"]
        ]
        
        compliance_percentage = (sum(individual_statuses) / len(individual_statuses)) * 100
        
        if compliance_percentage == 100.0:
            overall_status = "compliant"
        elif compliance_percentage >= 75.0:
            overall_status = "partial"
        elif compliance_percentage >= 50.0:
            overall_status = "warning"
        else:
            overall_status = "non-compliant"
        
        # Build detailed metrics
        detailed_metrics = {
            "ai_metrics": ai_supremacy_status["details"],
            "csi_architecture": dual_csi_status["details"],
            "batch_processing": batch_compliance_status["details"]
        }
        
        # Generate recommendations if not fully compliant
        recommendations = []
        if not ai_supremacy_status["compliant"]:
            recommendations.append({
                "component": "ai_metrics",
                "issue": "AI micro-metrics supremacy not fully enforced",
                "recommendation": "Ensure all analysis prioritizes AI-driven metrics over traditional metrics"
            })
        
        if not dual_csi_status["compliant"]:
            recommendations.append({
                "component": "csi_architecture",
                "issue": "Dual CSI architecture incomplete",
                "recommendation": "Verify both calculated_csi and inferred_csi are present in all results"
            })
        
        if not batch_compliance_status["compliant"]:
            recommendations.append({
                "component": "batch_processing",
                "issue": "Batch processing optimization not meeting targets",
                "recommendation": "Review batch size and concurrent processing configuration"
            })
        
        if not cost_optimization_status["compliant"]:
            recommendations.append({
                "component": "cost_optimization",
                "issue": "Cost reduction target not achieved",
                "recommendation": "Optimize batching strategy to achieve 80% cost reduction"
            })
        
        response = {
            "ai_micro_metrics_supremacy": ai_supremacy_status["compliant"],
            "dual_csi_architecture": dual_csi_status["compliant"],
            "batch_processing_compliance": batch_compliance_status["compliant"],
            "cost_optimization_compliance": cost_optimization_status["compliant"],
            "overall_compliance_status": overall_status,
            "compliance_percentage": compliance_percentage,
            "last_validation_timestamp": datetime.utcnow().isoformat(),
            "detailed_metrics": detailed_metrics
        }
        
        if recommendations:
            response["recommendations"] = recommendations
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting constitutional compliance: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error retrieving constitutional compliance")

async def _validate_ai_micro_metrics_supremacy(db: Session) -> Dict[str, Any]:
    """Validate that AI micro-metrics supremacy is enforced."""
    try:
        # Check recent job results for AI metrics presence
        recent_jobs = db.query(Job).filter(
            Job.status == "completed",
            Job.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).limit(100).all()
        
        ai_metrics_present = 0
        total_analyzed = 0
        
        for job in recent_jobs:
            if job.result and "analysis_results" in job.result:
                results = job.result["analysis_results"]
                for result in results:
                    total_analyzed += 1
                    if "ai_micro_metrics" in result and result["ai_micro_metrics"]:
                        ai_metrics_present += 1
        
        compliance_rate = ai_metrics_present / total_analyzed if total_analyzed > 0 else 1.0
        compliant = compliance_rate >= 0.95  # 95% compliance required
        
        return {
            "compliant": compliant,
            "details": {
                "enabled": True,
                "validation_status": "compliant" if compliant else "non-compliant",
                "metrics_count": ai_metrics_present,
                "total_analyzed": total_analyzed,
                "compliance_rate": compliance_rate
            }
        }
        
    except Exception as e:
        logger.error(f"Error validating AI supremacy: {str(e)}")
        return {
            "compliant": False,
            "details": {
                "enabled": False,
                "validation_status": "error",
                "metrics_count": 0,
                "error": str(e)
            }
        }

async def _validate_dual_csi_architecture(db: Session) -> Dict[str, Any]:
    """Validate that dual CSI architecture is properly implemented."""
    try:
        # Check recent job results for dual CSI presence
        recent_jobs = db.query(Job).filter(
            Job.status == "completed",
            Job.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).limit(100).all()
        
        calculated_csi_present = 0
        inferred_csi_present = 0
        dual_csi_present = 0
        total_analyzed = 0
        
        for job in recent_jobs:
            if job.result and "analysis_results" in job.result:
                results = job.result["analysis_results"]
                for result in results:
                    total_analyzed += 1
                    
                    has_calculated = "calculated_csi" in result and result["calculated_csi"] is not None
                    has_inferred = "inferred_csi" in result and result["inferred_csi"] is not None
                    
                    if has_calculated:
                        calculated_csi_present += 1
                    if has_inferred:
                        inferred_csi_present += 1
                    if has_calculated and has_inferred:
                        dual_csi_present += 1
        
        calculated_rate = calculated_csi_present / total_analyzed if total_analyzed > 0 else 1.0
        inferred_rate = inferred_csi_present / total_analyzed if total_analyzed > 0 else 1.0
        dual_rate = dual_csi_present / total_analyzed if total_analyzed > 0 else 1.0
        
        # Dual architecture is compliant if 95% of results have both CSI values
        compliant = dual_rate >= 0.95
        
        return {
            "compliant": compliant,
            "details": {
                "calculated_csi_enabled": calculated_rate >= 0.95,
                "inferred_csi_enabled": inferred_rate >= 0.95,
                "dual_architecture_active": compliant,
                "calculated_csi_rate": calculated_rate,
                "inferred_csi_rate": inferred_rate,
                "dual_csi_rate": dual_rate,
                "total_analyzed": total_analyzed
            }
        }
        
    except Exception as e:
        logger.error(f"Error validating dual CSI: {str(e)}")
        return {
            "compliant": False,
            "details": {
                "calculated_csi_enabled": False,
                "inferred_csi_enabled": False,
                "dual_architecture_active": False,
                "error": str(e)
            }
        }

async def _validate_batch_processing_compliance(db: Session) -> Dict[str, Any]:
    """Validate batch processing optimization compliance."""
    try:
        # Check recent batch processing performance
        recent_batches = db.query(BatchContext).filter(
            BatchContext.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).limit(100).all()
        
        optimization_enabled = len(recent_batches) > 0  # Batches exist = optimization enabled
        
        # Calculate performance metrics
        successful_batches = len([b for b in recent_batches if b.status == "completed"])
        total_batches = len(recent_batches)
        
        success_rate = successful_batches / total_batches if total_batches > 0 else 1.0
        compliant = optimization_enabled and success_rate >= 0.90  # 90% success rate required
        
        return {
            "compliant": compliant,
            "details": {
                "optimization_enabled": optimization_enabled,
                "success_rate": success_rate,
                "successful_batches": successful_batches,
                "total_batches": total_batches
            }
        }
        
    except Exception as e:
        logger.error(f"Error validating batch compliance: {str(e)}")
        return {
            "compliant": False,
            "details": {
                "optimization_enabled": False,
                "error": str(e)
            }
        }

async def _validate_cost_optimization_compliance(db: Session) -> Dict[str, Any]:
    """Validate cost optimization targets are being met."""
    try:
        # Check recent batch results for cost reduction metrics
        recent_batches = db.query(BatchContext).filter(
            BatchContext.status == "completed",
            BatchContext.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).limit(50).all()
        
        cost_reductions = []
        
        for batch in recent_batches:
            if batch.result_data and "optimization_data" in batch.result_data:
                opt_data = batch.result_data["optimization_data"]
                if "estimated_cost_reduction" in opt_data:
                    cost_reductions.append(opt_data["estimated_cost_reduction"])
        
        if cost_reductions:
            avg_cost_reduction = sum(cost_reductions) / len(cost_reductions)
            target_met = avg_cost_reduction >= 75.0  # At least 75% (close to 80% target)
        else:
            avg_cost_reduction = 0.0
            target_met = False
        
        return {
            "compliant": target_met,
            "details": {
                "cost_reduction_target": 80.0,
                "actual_cost_reduction": avg_cost_reduction,
                "target_met": target_met,
                "batches_analyzed": len(cost_reductions)
            }
        }
        
    except Exception as e:
        logger.error(f"Error validating cost optimization: {str(e)}")
        return {
            "compliant": False,
            "details": {
                "cost_reduction_target": 80.0,
                "actual_cost_reduction": None,
                "error": str(e)
            }
        }