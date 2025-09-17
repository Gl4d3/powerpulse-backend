#!/usr/bin/env python3
"""
End-to-End Test for AI-Enhanced Interaction Analysis Pipeline

This script tests the complete pipeline:
1. Reset database to clean state
2. Upload FB17-23.json via /api/upload-interaction-json endpoint
3. Process conversations with hybrid AI boundary detection
4. Verify CSI scores and interaction analysis results
5. Log API calls, token usage, and performance metrics
6. Generate comprehensive test report

Author: GitHub Copilot
Date: September 17, 2025
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import project modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from database import SessionLocal, engine
from models import Base, Conversation, InteractionAnalysis, Job, JobMetric
from services.csi_analysis_pipeline import CSIAnalysisPipeline
from services.file_service_optimized import optimized_file_service
import config

class E2ETestReport:
    """Comprehensive test report generator"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            'test_metadata': {
                'start_time': self.start_time.isoformat(),
                'test_version': '1.0',
                'pipeline_version': '6.0 - AI Enhanced'
            },
            'database_reset': {},
            'file_upload': {},
            'pipeline_processing': {},
            'ai_usage_metrics': {},
            'csi_validation': {},
            'performance_metrics': {},
            'errors': []
        }
    
    def add_result(self, section: str, data: Dict[str, Any]):
        """Add results to specific section"""
        self.results[section].update(data)
    
    def add_error(self, error_msg: str):
        """Add error to report"""
        self.results['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'error': error_msg
        })
        logger.error(error_msg)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate final test report"""
        self.results['test_metadata']['end_time'] = datetime.now().isoformat()
        self.results['test_metadata']['total_duration_seconds'] = (
            datetime.now() - self.start_time
        ).total_seconds()
        return self.results

async def reset_database():
    """Reset database to clean state for testing"""
    logger.info("Resetting database to clean state...")
    
    try:
        # Drop all tables and recreate
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # Verify clean state
        db = SessionLocal()
        conversation_count = db.query(Conversation).count()
        interaction_count = db.query(InteractionAnalysis).count()
        job_count = db.query(Job).count()
        db.close()
        
        result = {
            'success': True,
            'conversations_before': conversation_count,
            'interactions_before': interaction_count,  
            'jobs_before': job_count,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Database reset complete: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Database reset failed: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

async def upload_test_file():
    """Upload FB17-23.json file for interaction analysis"""
    logger.info("Uploading test file FB17-23.json...")
    
    try:
        # Read test file
        test_file_path = Path(__file__).parent.parent / 'attached_assets' / 'FB17-23.json'
        if not test_file_path.exists():
            raise FileNotFoundError(f"Test file not found: {test_file_path}")
        
        with open(test_file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Parse JSON to get stats
        data = json.loads(file_content)
        conversations_in_file = len(data) if isinstance(data, dict) else 1
        total_messages = sum(len(msgs) for msgs in data.values()) if isinstance(data, dict) else 0
        
        # Process file through file service (simulating upload endpoint)
        db = SessionLocal()
        upload_id = "e2e-test-" + str(int(time.time()))
        
        conversations_processed, messages_processed, jobs_created = await optimized_file_service.process_grouped_chats_json(
            db=db,
            file_content=file_content,
            upload_id=upload_id,
            force_reprocess=True  # Ensure processing
        )
        
        db.close()
        
        result = {
            'success': True,
            'upload_id': upload_id,
            'file_size_kb': len(file_content) // 1024,
            'conversations_in_file': conversations_in_file,
            'total_messages_in_file': total_messages,
            'conversations_processed': conversations_processed,
            'messages_processed': messages_processed,
            'jobs_created': jobs_created,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"File upload complete: {result}")
        return result
        
    except Exception as e:
        error_msg = f"File upload failed: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

async def run_interaction_analysis():
    """Run AI-enhanced interaction analysis pipeline"""
    logger.info("Starting AI-enhanced interaction analysis pipeline...")
    
    try:
        db = SessionLocal()
        
        # Get all conversations for processing
        conversations = db.query(Conversation).all()
        conversation_ids = [c.id for c in conversations]
        
        if not conversation_ids:
            raise ValueError("No conversations found to process")
        
        logger.info(f"Processing {len(conversation_ids)} conversations with AI-enhanced pipeline")
        
        # Initialize CSI Analysis Pipeline
        pipeline = CSIAnalysisPipeline(db)
        
        # Track processing metrics
        start_time = time.time()
        
        # Process conversations in batch (using new batch AI enhancement)
        batch_result = await pipeline.process_batch(conversation_ids)
        
        end_time = time.time()
        processing_duration = end_time - start_time
        
        # Collect results
        result = {
            'success': True,
            'conversations_processed': batch_result.total_conversations,
            'successful_conversations': batch_result.successful_conversations,
            'total_interactions_detected': batch_result.total_interactions,
            'average_csi_score': batch_result.avg_csi_score,
            'processing_duration_seconds': processing_duration,
            'total_tokens_used': batch_result.total_tokens,
            'errors_count': len(batch_result.errors),
            'detailed_errors': batch_result.errors[:5],  # First 5 errors
            'timestamp': datetime.now().isoformat()
        }
        
        # Get interaction analysis records from database
        interaction_analyses = db.query(InteractionAnalysis).all()
        
        result['interaction_analyses'] = {
            'total_records': len(interaction_analyses),
            'avg_csi_scores': {
                'effectiveness': sum(ia.effectiveness_score for ia in interaction_analyses if ia.effectiveness_score) / len([ia for ia in interaction_analyses if ia.effectiveness_score]) if interaction_analyses else 0,
                'effort': sum(ia.effort_score for ia in interaction_analyses if ia.effort_score) / len([ia for ia in interaction_analyses if ia.effort_score]) if interaction_analyses else 0,  
                'efficiency': sum(ia.efficiency_score for ia in interaction_analyses if ia.efficiency_score) / len([ia for ia in interaction_analyses if ia.efficiency_score]) if interaction_analyses else 0,
                'empathy': sum(ia.empathy_score for ia in interaction_analyses if ia.empathy_score) / len([ia for ia in interaction_analyses if ia.empathy_score]) if interaction_analyses else 0,
                'overall_csi': sum(ia.overall_csi for ia in interaction_analyses if ia.overall_csi) / len([ia for ia in interaction_analyses if ia.overall_csi]) if interaction_analyses else 0
            },
            'boundary_methods_used': list(set(ia.boundary_method for ia in interaction_analyses if ia.boundary_method)),
            'confidence_stats': {
                'avg_confidence': sum(ia.boundary_confidence for ia in interaction_analyses if ia.boundary_confidence) / len([ia for ia in interaction_analyses if ia.boundary_confidence]) if interaction_analyses else 0,
                'high_confidence_count': len([ia for ia in interaction_analyses if ia.boundary_confidence and ia.boundary_confidence >= 0.8]),
                'ai_enhanced_count': len([ia for ia in interaction_analyses if ia.boundary_method and 'ai' in ia.boundary_method.lower()])
            }
        }
        
        db.close()
        
        logger.info(f"Pipeline processing complete: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Interaction analysis failed: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

async def validate_csi_scores():
    """Validate CSI scores and data integrity"""
    logger.info("Validating CSI scores and data integrity...")
    
    try:
        db = SessionLocal()
        
        # Get all interaction analyses
        interaction_analyses = db.query(InteractionAnalysis).all()
        
        validation_results = {
            'total_interactions': len(interaction_analyses),
            'non_null_csi_scores': len([ia for ia in interaction_analyses if ia.overall_csi is not None and ia.overall_csi > 0]),
            'score_ranges': {
                'effectiveness': {'min': 0, 'max': 0, 'avg': 0, 'count': 0},
                'effort': {'min': 0, 'max': 0, 'avg': 0, 'count': 0},
                'efficiency': {'min': 0, 'max': 0, 'avg': 0, 'count': 0},
                'empathy': {'min': 0, 'max': 0, 'avg': 0, 'count': 0},
                'overall_csi': {'min': 0, 'max': 0, 'avg': 0, 'count': 0}
            },
            'data_quality_checks': {
                'has_message_count': len([ia for ia in interaction_analyses if ia.message_count and ia.message_count > 0]),
                'has_duration': len([ia for ia in interaction_analyses if ia.interaction_duration and ia.interaction_duration > 0]),
                'has_boundary_method': len([ia for ia in interaction_analyses if ia.boundary_method]),
                'has_confidence': len([ia for ia in interaction_analyses if ia.boundary_confidence is not None])
            }
        }
        
        # Calculate score statistics
        for score_type in ['effectiveness_score', 'effort_score', 'efficiency_score', 'empathy_score', 'overall_csi']:
            scores = [getattr(ia, score_type) for ia in interaction_analyses if getattr(ia, score_type) is not None and getattr(ia, score_type) > 0]
            if scores:
                key = score_type.replace('_score', '')
                validation_results['score_ranges'][key] = {
                    'min': min(scores),
                    'max': max(scores),
                    'avg': sum(scores) / len(scores),
                    'count': len(scores)
                }
        
        # Check for invalid scores (outside expected ranges)
        validation_issues = []
        for ia in interaction_analyses:
            if ia.overall_csi and (ia.overall_csi < 0 or ia.overall_csi > 10):
                validation_issues.append(f"Invalid CSI score for interaction {ia.id}: {ia.overall_csi}")
        
        validation_results['validation_issues'] = validation_issues
        validation_results['data_integrity_passed'] = len(validation_issues) == 0
        
        db.close()
        
        result = {
            'success': True,
            'validation': validation_results,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"CSI validation complete: {result}")
        return result
        
    except Exception as e:
        error_msg = f"CSI validation failed: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

async def collect_performance_metrics():
    """Collect detailed performance and AI usage metrics"""
    logger.info("Collecting performance and AI usage metrics...")
    
    try:
        db = SessionLocal()
        
        # Get job metrics
        jobs = db.query(Job).all()
        job_metrics = db.query(JobMetric).all()
        
        performance_data = {
            'jobs': {
                'total_jobs': len(jobs),
                'completed_jobs': len([j for j in jobs if j.status == 'completed']),
                'failed_jobs': len([j for j in jobs if j.status == 'failed']),
                'pending_jobs': len([j for j in jobs if j.status == 'pending'])
            },
            'job_metrics': {
                'total_metrics': len(job_metrics),
                'total_tokens': sum(jm.token_usage for jm in job_metrics if jm.token_usage),
                'total_api_calls': sum(jm.api_calls_made for jm in job_metrics if jm.api_calls_made),
                'avg_processing_time': sum(jm.processing_time_seconds for jm in job_metrics if jm.processing_time_seconds) / len(job_metrics) if job_metrics else 0
            },
            'ai_usage_analysis': {
                'estimated_cost_usd': 0,  # Would calculate based on Gemini pricing
                'tokens_per_conversation': 0,
                'batch_efficiency_gain': 'N/A'  # Compare single vs batch API calls
            }
        }
        
        # Calculate AI usage efficiency
        if jobs:
            conversations_count = db.query(Conversation).count()
            if conversations_count > 0:
                performance_data['ai_usage_analysis']['tokens_per_conversation'] = (
                    performance_data['job_metrics']['total_tokens'] / conversations_count
                )
        
        db.close()
        
        result = {
            'success': True,
            'performance': performance_data,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Performance metrics collected: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Performance metrics collection failed: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

async def main():
    """Run comprehensive E2E test"""
    logger.info("=== Starting Comprehensive E2E Test for AI-Enhanced Interaction Analysis ===")
    
    report = E2ETestReport()
    
    try:
        # Step 1: Reset Database
        logger.info("Step 1: Resetting database...")
        db_result = await reset_database()
        report.add_result('database_reset', db_result)
        if not db_result.get('success'):
            raise Exception("Database reset failed")
        
        # Step 2: Upload Test File
        logger.info("Step 2: Uploading test file...")
        upload_result = await upload_test_file()
        report.add_result('file_upload', upload_result)
        if not upload_result.get('success'):
            raise Exception("File upload failed")
        
        # Step 3: Run Interaction Analysis Pipeline
        logger.info("Step 3: Running AI-enhanced interaction analysis...")
        pipeline_result = await run_interaction_analysis()
        report.add_result('pipeline_processing', pipeline_result)
        if not pipeline_result.get('success'):
            raise Exception("Pipeline processing failed")
        
        # Step 4: Validate CSI Scores
        logger.info("Step 4: Validating CSI scores...")
        validation_result = await validate_csi_scores()
        report.add_result('csi_validation', validation_result)
        
        # Step 5: Collect Performance Metrics
        logger.info("Step 5: Collecting performance metrics...")
        performance_result = await collect_performance_metrics()
        report.add_result('performance_metrics', performance_result)
        
        logger.info("=== E2E Test Complete ===")
        
    except Exception as e:
        error_msg = f"E2E Test failed: {str(e)}"
        report.add_error(error_msg)
        logger.error(error_msg)
    
    # Generate final report
    final_report = report.generate_report()
    
    # Save report to file
    report_path = Path(__file__).parent.parent / 'docs' / 'case-analysis' / 'e2e_test_report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(final_report, f, indent=2)
    
    logger.info(f"Test report saved to: {report_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("E2E TEST SUMMARY")
    print("="*60)
    print(f"Test Duration: {final_report['test_metadata']['total_duration_seconds']:.2f} seconds")
    print(f"Database Reset: {'✓' if final_report['database_reset'].get('success') else '✗'}")
    print(f"File Upload: {'✓' if final_report['file_upload'].get('success') else '✗'}")
    print(f"Pipeline Processing: {'✓' if final_report['pipeline_processing'].get('success') else '✗'}")
    print(f"CSI Validation: {'✓' if final_report['csi_validation'].get('success') else '✗'}")
    print(f"Performance Metrics: {'✓' if final_report['performance_metrics'].get('success') else '✗'}")
    print(f"Total Errors: {len(final_report['errors'])}")
    
    if final_report['pipeline_processing'].get('success'):
        pp = final_report['pipeline_processing']
        print(f"\nPipeline Results:")
        print(f"  - Conversations Processed: {pp.get('conversations_processed', 0)}")
        print(f"  - Interactions Detected: {pp.get('total_interactions_detected', 0)}")
        print(f"  - Average CSI Score: {pp.get('average_csi_score', 0):.2f}")
        print(f"  - Processing Duration: {pp.get('processing_duration_seconds', 0):.2f}s")
        print(f"  - Total Tokens Used: {pp.get('total_tokens_used', 0)}")
    
    print("="*60)
    return final_report

if __name__ == "__main__":
    asyncio.run(main())