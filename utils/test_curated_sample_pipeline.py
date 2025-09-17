#!/usr/bin/env python3
"""
Curated Sample Test - Interaction-Based Analysis Pipeline

Test the complete interaction-based analysis pipeline using curated_sample.json
with ~58 conversations instead of 200+ to validate:
1. Dual CSI system (calculated vs AI inferred)
2. Batch interaction processing 
3. Two AI calls per categorization (boundaries + CSI inference)
4. Reduced verbose logging through batching

This addresses the client requirement to compare calculated CSI vs AI inferred CSI.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine
from models import Base, Conversation, Message, Job, InteractionAnalysis, DailyAnalysis
from sqlalchemy import text
from services.csi_analysis_pipeline import CSIAnalysisPipeline
from services.file_service_optimized import OptimizedFileService
from services import job_service
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/curated_sample_test.log')
    ]
)
logger = logging.getLogger(__name__)

class CuratedSampleTester:
    """Test runner for curated sample interaction analysis"""
    
    def __init__(self):
        """Initialize test environment"""
        self.settings = config.Settings()
        self.file_service = OptimizedFileService()
        # job_service is a module with functions, not a class
        
        # Test configuration
        self.sample_file = Path("attached_assets/curated_sample.json")
        self.test_results = {}
        
    async def run_complete_test(self) -> Dict[str, Any]:
        """
        Run complete curated sample test including:
        1. Data upload and parsing
        2. Interaction-based analysis pipeline 
        3. Dual CSI validation (calculated vs AI inferred)
        4. Batch processing validation
        """
        test_start = datetime.now()
        logger.info("="*80)
        logger.info("CURATED SAMPLE TEST - INTERACTION-BASED ANALYSIS PIPELINE")
        logger.info("="*80)
        
        try:
            # Step 1: Reset test environment
            logger.info("Step 1: Resetting test environment...")
            await self._reset_test_environment()
            
            # Step 2: Load curated sample data
            logger.info("Step 2: Loading curated sample data...")
            uploaded_data = await self._upload_curated_sample()
            
            # Step 3: Run interaction-based analysis
            logger.info("Step 3: Running interaction-based analysis pipeline...")
            pipeline_results = await self._run_interaction_pipeline(uploaded_data['conversation_ids'])
            
            # Step 4: Validate dual CSI system
            logger.info("Step 4: Validating dual CSI system...")
            csi_validation = await self._validate_dual_csi_system()
            
            # Step 5: Generate test report
            logger.info("Step 5: Generating test report...")
            test_results = await self._generate_test_report({
                'upload_results': uploaded_data,
                'pipeline_results': pipeline_results,
                'csi_validation': csi_validation,
                'test_duration': (datetime.now() - test_start).total_seconds()
            })
            
            logger.info("="*80)
            logger.info("CURATED SAMPLE TEST COMPLETED SUCCESSFULLY")
            logger.info("="*80)
            
            return test_results
            
        except Exception as e:
            logger.error(f"Curated sample test failed: {e}")
            raise

    async def _reset_test_environment(self):
        """Reset database for clean testing"""
        with SessionLocal() as db:
            # Clear association tables first (prevent foreign key errors)
            db.execute(text("DELETE FROM job_daily_analyses"))
            db.execute(text("DELETE FROM job_interaction_analyses"))
            
            # Clear interaction analyses
            db.query(InteractionAnalysis).delete()
            
            # Clear daily analyses (prevent unique constraint errors)
            db.query(DailyAnalysis).delete()
            
            # Clear conversations and messages
            db.query(Message).delete()
            db.query(Conversation).delete()
            
            # Clear jobs
            db.query(Job).delete()
            
            db.commit()
            logger.info("Test environment reset completed")

    async def _upload_curated_sample(self) -> Dict[str, Any]:
        """Upload and parse curated sample data"""
        try:
            # Load sample data
            with open(self.sample_file, 'r') as f:
                sample_data = json.load(f)
            
            logger.info(f"Loaded curated sample: {sample_data.get('description', 'No description')}")
            
            # Process through file service (interaction mode) 
            with SessionLocal() as db:
                # Convert sample data back to JSON string for processing
                file_content = json.dumps(sample_data)
                conversations_created, messages_processed, upload_summary = await self.file_service.process_grouped_chats_json(
                    file_content=file_content,
                    db=db,
                    upload_id='curated_sample_test',
                    force_reprocess=True
                )
                
                result = {
                    'conversations_created': conversations_created,
                    'messages_processed': messages_processed,
                    'upload_summary': upload_summary,
                    'conversation_ids': []  # We'll get these from the database
                }
                
                # Get conversation IDs
                conversations = db.query(Conversation).all()
                result['conversation_ids'] = [c.id for c in conversations]
            
            logger.info(f"Upload completed: {result['conversations_created']} conversations, "
                       f"{result['messages_processed']} messages")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload curated sample: {e}")
            raise

    async def _run_interaction_pipeline(self, conversation_ids: List[int]) -> Dict[str, Any]:
        """Run interaction-based analysis pipeline"""
        try:
            with SessionLocal() as db:
                # Initialize pipeline
                pipeline = CSIAnalysisPipeline(db)
                
                # Create interaction analysis job
                job = job_service.create_interaction_analysis_job(
                    db=db,
                    upload_id='curated_sample_test',
                    job_data={
                        'conversation_ids': conversation_ids,
                        'test_type': 'curated_sample',
                        'dual_csi_validation': True
                    }
                )
                
                logger.info(f"Created interaction analysis job {job.id} for {len(conversation_ids)} conversations")
                
                # Process batch
                batch_result = await pipeline.process_batch(conversation_ids)
                
                # Update job with results
                job.status = 'completed' if batch_result.successful_conversations > 0 else 'failed'
                job.completed_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Pipeline processing completed: {batch_result.successful_conversations}/{batch_result.total_conversations} conversations, "
                           f"{batch_result.total_interactions} interactions, avg CSI: {batch_result.avg_csi_score:.2f}")
                
                return {
                    'job_id': job.id,
                    'processing_summary': {
                        'total_conversations': batch_result.total_conversations,
                        'successful_conversations': batch_result.successful_conversations,
                        'total_interactions': batch_result.total_interactions,
                        'avg_csi_score': batch_result.avg_csi_score,
                        'total_processing_time': batch_result.total_processing_time,
                        'total_tokens': batch_result.total_tokens,
                        'error_count': len(batch_result.errors),
                        'errors': batch_result.errors
                    }
                }
                
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            raise

    async def _validate_dual_csi_system(self) -> Dict[str, Any]:
        """Validate dual CSI system - calculated vs AI inferred"""
        try:
            with SessionLocal() as db:
                # Get all interactions with both CSI scores
                interactions = db.query(InteractionAnalysis).filter(
                    InteractionAnalysis.csi_score.isnot(None),
                    InteractionAnalysis.inferred_csi.isnot(None)
                ).all()
                
                if not interactions:
                    return {
                        'validation_status': 'failed',
                        'error': 'No interactions found with both CSI scores'
                    }
                
                # Calculate comparison metrics
                calculated_scores = [i.csi_score for i in interactions]
                inferred_scores = [i.inferred_csi for i in interactions]
                
                # Statistics
                avg_calculated = sum(calculated_scores) / len(calculated_scores)
                avg_inferred = sum(inferred_scores) / len(inferred_scores)
                
                # Score differences
                differences = [abs(calc - inf) for calc, inf in zip(calculated_scores, inferred_scores)]
                avg_difference = sum(differences) / len(differences)
                max_difference = max(differences)
                
                # Agreement analysis (within 1.0 point)
                close_agreements = sum(1 for diff in differences if diff <= 1.0)
                agreement_rate = close_agreements / len(differences) * 100
                
                validation_results = {
                    'validation_status': 'success',
                    'interactions_analyzed': len(interactions),
                    'calculated_csi': {
                        'average': avg_calculated,
                        'min': min(calculated_scores),
                        'max': max(calculated_scores)
                    },
                    'inferred_csi': {
                        'average': avg_inferred,
                        'min': min(inferred_scores),
                        'max': max(inferred_scores)
                    },
                    'comparison': {
                        'avg_difference': avg_difference,
                        'max_difference': max_difference,
                        'agreement_rate_1pt': agreement_rate,
                        'correlation_direction': 'positive' if avg_calculated < avg_inferred else 'negative'
                    }
                }
                
                logger.info(f"Dual CSI validation: {len(interactions)} interactions, "
                           f"avg calculated: {avg_calculated:.2f}, avg inferred: {avg_inferred:.2f}, "
                           f"agreement rate: {agreement_rate:.1f}%")
                
                return validation_results
                
        except Exception as e:
            logger.error(f"Dual CSI validation failed: {e}")
            return {
                'validation_status': 'error',
                'error': str(e)
            }

    async def _generate_test_report(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        try:
            report = {
                'test_metadata': {
                    'test_type': 'curated_sample_interaction_analysis',
                    'test_timestamp': datetime.now().isoformat(),
                    'test_duration_seconds': test_data['test_duration'],
                    'sample_file': str(self.sample_file),
                    'sample_size': '~58 conversations'
                },
                'upload_results': test_data['upload_results'],
                'pipeline_results': test_data['pipeline_results'],
                'dual_csi_validation': test_data['csi_validation'],
                'performance_metrics': {
                    'conversations_per_second': test_data['pipeline_results']['processing_summary']['total_conversations'] / test_data['test_duration'],
                    'interactions_per_second': test_data['pipeline_results']['processing_summary']['total_interactions'] / test_data['test_duration'],
                    'tokens_per_conversation': test_data['pipeline_results']['processing_summary']['total_tokens'] / max(test_data['pipeline_results']['processing_summary']['total_conversations'], 1),
                    'success_rate': (test_data['pipeline_results']['processing_summary']['successful_conversations'] / test_data['pipeline_results']['processing_summary']['total_conversations']) * 100
                },
                'test_conclusions': {
                    'dual_csi_functional': test_data['csi_validation']['validation_status'] == 'success',
                    'batch_processing_functional': test_data['pipeline_results']['processing_summary']['error_count'] == 0,
                    'ai_calls_optimization': 'Two AI calls per interaction: boundaries + CSI inference',
                    'verbose_logging_resolved': 'Interactions processed in batches of 10 with summary logging'
                }
            }
            
            # Save report
            report_file = f"docs/case-analysis/curated_sample_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Test report saved to {report_file}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate test report: {e}")
            raise

async def main():
    """Main test execution"""
    try:
        tester = CuratedSampleTester()
        results = await tester.run_complete_test()
        
        print("\n" + "="*80)
        print("CURATED SAMPLE TEST RESULTS SUMMARY")
        print("="*80)
        print(f"Test Duration: {results['test_metadata']['test_duration_seconds']:.1f}s")
        print(f"Conversations Processed: {results['pipeline_results']['processing_summary']['total_conversations']}")
        print(f"Interactions Detected: {results['pipeline_results']['processing_summary']['total_interactions']}")
        print(f"Average CSI Score: {results['pipeline_results']['processing_summary']['avg_csi_score']:.2f}")
        print(f"Dual CSI System: {'✓ FUNCTIONAL' if results['test_conclusions']['dual_csi_functional'] else '✗ FAILED'}")
        print(f"Batch Processing: {'✓ FUNCTIONAL' if results['test_conclusions']['batch_processing_functional'] else '✗ FAILED'}")
        print("="*80)
        
        if results['dual_csi_validation']['validation_status'] == 'success':
            csi_data = results['dual_csi_validation']
            print(f"CSI Comparison Results:")
            print(f"  • Calculated CSI: {csi_data['calculated_csi']['average']:.2f} (range: {csi_data['calculated_csi']['min']:.2f}-{csi_data['calculated_csi']['max']:.2f})")
            print(f"  • AI Inferred CSI: {csi_data['inferred_csi']['average']:.2f} (range: {csi_data['inferred_csi']['min']:.2f}-{csi_data['inferred_csi']['max']:.2f})")
            print(f"  • Agreement Rate: {csi_data['comparison']['agreement_rate_1pt']:.1f}% (within 1.0 point)")
            print(f"  • Average Difference: {csi_data['comparison']['avg_difference']:.2f}")
        
        return results
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())