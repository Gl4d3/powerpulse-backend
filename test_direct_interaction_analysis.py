#!/usr/bin/env python3
"""
Direct Test of Interaction Analysis Pipeline
Bypasses HTTP to test the core functionality directly
"""

import asyncio
import logging
import json
from pathlib import Path

# Setup
import sys
sys.path.append('.')

from database import SessionLocal
from services.file_service_optimized import OptimizedFileService
from services.csi_analysis_pipeline import CSIAnalysisPipeline
from models import Conversation, InteractionAnalysis

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_direct_interaction_analysis():
    """Test the complete interaction analysis pipeline directly"""
    
    logger.info("=== DIRECT INTERACTION ANALYSIS TEST ===")
    
    # Load curated sample
    curated_sample_path = Path("attached_assets/curated_sample.json")
    
    if not curated_sample_path.exists():
        logger.error(f"Curated sample not found at {curated_sample_path}")
        return False
    
    try:
        # Read sample data
        with open(curated_sample_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        sample_data = json.loads(file_content)
        logger.info(f"Loaded sample: {sample_data.get('description', 'No description')}")
        
        with SessionLocal() as db:
            # Clear previous test data
            logger.info("Clearing previous test data...")
            db.query(InteractionAnalysis).delete()
            db.query(Conversation).delete()
            db.commit()
            
            # Step 1: Process file to create conversations
            logger.info("Step 1: Processing file to create conversations...")
            file_service = OptimizedFileService()
            
            conversations_created, messages_processed, upload_summary = await file_service.process_grouped_chats_json(
                file_content=file_content,
                db=db,
                upload_id='direct_test',
                force_reprocess=True
            )
            
            logger.info(f"Created {conversations_created} conversations, {messages_processed} messages")
            
            # Step 2: Get conversation IDs
            conversations = db.query(Conversation).all()
            conversation_ids = [c.id for c in conversations]
            logger.info(f"Found {len(conversation_ids)} conversations to analyze")
            
            if not conversation_ids:
                logger.error("No conversations found - file processing failed")
                return False
            
            # Step 3: Run interaction analysis pipeline
            logger.info("Step 2: Running interaction analysis pipeline...")
            pipeline = CSIAnalysisPipeline(db)
            
            # Test with just first 5 conversations to avoid long processing
            test_conversation_ids = conversation_ids[:5]
            logger.info(f"Testing with {len(test_conversation_ids)} conversations for speed")
            
            batch_result = await pipeline.process_batch(test_conversation_ids)
            
            logger.info("=== PIPELINE RESULTS ===")
            logger.info(f"Total conversations: {batch_result.total_conversations}")
            logger.info(f"Successful conversations: {batch_result.successful_conversations}")
            logger.info(f"Total interactions: {batch_result.total_interactions}")
            logger.info(f"Average CSI score: {batch_result.avg_csi_score:.2f}")
            logger.info(f"Processing time: {batch_result.total_processing_time:.2f}s")
            logger.info(f"Total tokens: {batch_result.total_tokens}")
            logger.info(f"Errors: {len(batch_result.errors)}")
            
            if batch_result.errors:
                logger.warning("Errors encountered:")
                for error in batch_result.errors[:5]:  # Show first 5 errors
                    logger.warning(f"  - {error}")
            
            # Step 4: Check for dual CSI data
            logger.info("Step 3: Checking dual CSI results...")
            interactions = db.query(InteractionAnalysis).all()
            
            calculated_csi_count = sum(1 for i in interactions if i.csi_score is not None)
            inferred_csi_count = sum(1 for i in interactions if i.inferred_csi is not None)
            
            logger.info(f"Interactions created: {len(interactions)}")
            logger.info(f"Calculated CSI scores: {calculated_csi_count}")
            logger.info(f"AI Inferred CSI scores: {inferred_csi_count}")
            
            # Show sample results
            if interactions:
                sample = interactions[0]
                logger.info("=== SAMPLE INTERACTION RESULT ===")
                logger.info(f"Interaction ID: {sample.id}")
                logger.info(f"Calculated CSI: {sample.csi_score}")
                logger.info(f"AI Inferred CSI: {sample.inferred_csi}")
                logger.info(f"Effectiveness: {sample.effectiveness_score}")
                logger.info(f"Effort: {sample.effort_score}")
                logger.info(f"Efficiency: {sample.efficiency_score}")
                logger.info(f"Empathy: {sample.empathy_score}")
                logger.info(f"Boundary Method: {sample.boundary_method}")
                logger.info(f"Confidence: {sample.boundary_confidence}")
            
            # Validate success
            success = (
                batch_result.successful_conversations > 0 and
                batch_result.total_interactions > 0 and
                calculated_csi_count > 0
            )
            
            if success:
                logger.info("✅ DUAL CSI SYSTEM TEST PASSED!")
                if inferred_csi_count > 0:
                    logger.info("✅ AI INFERRED CSI WORKING!")
                else:
                    logger.warning("⚠️ AI INFERRED CSI NOT GENERATED - Check Gemini API")
            else:
                logger.error("❌ TEST FAILED - No valid results generated")
            
            return success
            
    except Exception as e:
        logger.error(f"❌ ERROR during direct test: {e}", exc_info=True)
        return False

async def main():
    """Main test function"""
    logger.info("Starting direct interaction analysis test...")
    
    success = await test_direct_interaction_analysis()
    
    if success:
        logger.info("\n✅ DIRECT INTERACTION ANALYSIS TEST COMPLETED SUCCESSFULLY!")
        logger.info("The dual CSI interaction analysis pipeline is working.")
    else:
        logger.error("\n❌ DIRECT INTERACTION ANALYSIS TEST FAILED!")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())