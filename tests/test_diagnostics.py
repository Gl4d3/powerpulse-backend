"""
Backend Diagnostic Tool - PowerPulse Pipeline Issue Detection
Tests all components to identify why GPT analysis is failing and fallback values are being used.
"""
import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import services
from services.gpt_service import OptimizedGPTService
from services.file_service_optimized import OptimizedFileService
from services.analytics_service import AnalyticsService
from services.progress_tracker import ProgressTracker
from models import Message, Conversation, ProcessedChat
from database import SessionLocal, init_db
from config import settings

class BackendDiagnostic:
    """Diagnostic tool to test PowerPulse backend components"""
    
    def __init__(self):
        self.gpt_service = None
        self.file_service = OptimizedFileService()
        self.analytics_service = AnalyticsService()
        self.progress_tracker = ProgressTracker()
        self.sample_data = None
        self.db = None
        
    async def run_diagnostic(self):
        """Run complete diagnostic on all components"""
        logger.info("🚀 Starting PowerPulse Backend Diagnostic")
        logger.info("=" * 60)
        
        try:
            # Initialize database and session
            init_db()
            self.db = SessionLocal()
            logger.info("✅ Database initialized and session created")

            # Clear database at the start
            await self._clear_database()

            # Phase 1: Load sample data
            await self._phase1_load_sample_data()
            
            # Phase 2: Test GPT service
            await self._phase2_test_gpt_service()
            
            # Phase 3: Test database operations
            await self._phase3_test_database()
            
            # Phase 4: Test complete pipeline
            await self._phase4_test_pipeline()
            
            logger.info("✅ Diagnostic completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Diagnostic failed: {e}")
            raise
        finally:
            if self.db:
                self.db.close()
    
    async def _phase1_load_sample_data(self):
        """Phase 1: Load and validate sample data"""
        logger.info("📁 PHASE 1: Loading Sample Data")
        logger.info("-" * 40)
        
        try:
            # Load sample data from snippet
            sample_path = "attached_assets/snippet_1755240593792.json"
            with open(sample_path, 'r', encoding='utf-8') as f:
                self.sample_data = json.load(f)
            
            logger.info(f"✅ Sample data loaded: {len(self.sample_data)} conversations")
            
            # Validate data structure
            for chat_id, messages in list(self.sample_data.items())[:5]: # Log first 5
                logger.info(f"  📝 Chat {chat_id}: {len(messages)} messages")
                for msg in messages[:2]:  # Show first 2 messages
                    logger.info(f"    - {msg.get('DIRECTION', 'unknown')}: {msg.get('MESSAGE_CONTENT', '')[:50]}...")
            
            logger.info("✅ Phase 1 completed: Sample data loaded and validated")
            
        except Exception as e:
            logger.error(f"❌ Phase 1 failed: {e}")
            raise
    
    async def _phase2_test_gpt_service(self):
        """Phase 2: Test GPT service directly"""
        logger.info("🤖 PHASE 2: Testing AI Service")
        logger.info("-" * 40)
        
        try:
            # Get AI service based on configuration
            if settings.AI_SERVICE.lower() == "gemini":
                from services.gemini_service import get_gemini_service
                ai_service = get_gemini_service(settings.GEMINI_API_KEY)
                logger.info("✅ Using Google Gemini for AI analysis")
            else:
                from services.gpt_service import get_optimized_gpt_service
                ai_service = get_optimized_gpt_service(settings.OPENAI_API_KEY)
                logger.info("✅ Using OpenAI GPT for AI analysis")

            # Test with first conversation
            first_chat_id = list(self.sample_data.keys())[0]
            first_conversation = {
                'chat_id': first_chat_id,
                'messages': self.sample_data[first_chat_id]
            }
            
            logger.info(f"🧪 Testing AI analysis on conversation: {first_chat_id}")
            logger.info(f"  📊 Messages to analyze: {len(first_conversation['messages'])}")
            
            # Test single conversation analysis
            result = await ai_service._analyze_single_conversation(first_conversation)
            
            logger.info("📋 AI Analysis Result:")
            logger.info(f"  - Satisfaction Score: {result.get('satisfaction_score')}")
            logger.info(f"  - Is Satisfied: {result.get('is_satisfied')}")
            logger.info(f"  - Resolution Achieved: {result.get('resolution_achieved')}")
            logger.info(f"  - Common Topics: {result.get('common_topics')}")
            logger.info(f"  - Message Analyses: {len(result.get('message_analyses', []))}")
            
            # Check if fallback values were used
            if result.get('satisfaction_score') == 3 and result.get('common_topics') == ['general inquiry']:
                logger.warning("⚠️  FALLBACK VALUES DETECTED! AI analysis failed")
            else:
                logger.info("✅ Real AI values detected - analysis successful")
            
            logger.info("✅ Phase 2 completed: AI service tested")
            
        except Exception as e:
            logger.error(f"❌ Phase 2 failed: {e}")
            raise
    
    async def _phase3_test_database(self):
        """Phase 3: Test database operations"""
        logger.info("️  PHASE 3: Testing Database Operations")
        logger.info("-" * 40)
        
        try:
            if not self.db:
                logger.error("❌ Database session not available")
                return

            # Test basic database operations
            test_result = self.db.execute(text("SELECT 1")).scalar()
            logger.info(f"✅ Database connection test: {test_result}")
            
            # Check existing data
            conv_count = self.db.query(Conversation).count()
            msg_count = self.db.query(Message).count()
            logger.info(f"📊 Current database state (should be empty):")
            logger.info(f"  - Conversations: {conv_count}")
            logger.info(f"  - Messages: {msg_count}")
            
            logger.info("✅ Phase 3 completed: Database operations tested")
            
        except Exception as e:
            logger.error(f"❌ Phase 3 failed: {e}")
            raise
    
    async def _phase4_test_pipeline(self):
        """Phase 4: Test complete pipeline integration"""
        logger.info("🔗 PHASE 4: Testing Complete Pipeline")
        logger.info("-" * 40)
        
        try:
            if not self.db:
                logger.error("❌ Database session not available")
                return

            # Test file processing with a small subset of sample data
            subset_data = dict(list(self.sample_data.items()))
            sample_json = json.dumps(subset_data)
            logger.info(f"🧪 Testing file processing with {len(subset_data)} conversations")
            
            # Get current counts
            conv_count_before = self.db.query(Conversation).count()
            msg_count_before = self.db.query(Message).count()

            # Process the sample data
            conversations_processed, messages_processed, upload_id = await self.file_service.process_grouped_chats_json(
                sample_json, 
                self.db, 
                force_reprocess=True
            )
            
            logger.info(f"📊 Pipeline Results:")
            logger.info(f"  - Conversations Processed: {conversations_processed}")
            logger.info(f"  - Messages Processed: {messages_processed}")
            logger.info(f"  - Upload ID: {upload_id}")
            
            # Check database after processing
            conv_count_after = self.db.query(Conversation).count()
            msg_count_after = self.db.query(Message).count()
            
            logger.info(f"📈 Database after processing:")
            logger.info(f"  - Conversations: {conv_count_after} (was {conv_count_before})")
            logger.info(f"  - Messages: {msg_count_after} (was {msg_count_before})")
            
            # Check if new data was added
            if conv_count_after > conv_count_before:
                logger.info("✅ New conversations added to database")
            else:
                logger.warning("⚠️  No new conversations added - pipeline may have failed")
            
            # Test metrics calculation
            metrics = self.analytics_service.calculate_and_cache_metrics(self.db)
            logger.info(f"📊 Calculated Metrics:")
            logger.info(f"  - CSAT: {metrics.get('csat_percentage')}%")
            logger.info(f"  - FCR: {metrics.get('fcr_percentage')}%")
            logger.info(f"  - Avg Response Time: {metrics.get('avg_response_time_minutes')} min")
            
            logger.info("✅ Phase 4 completed: Complete pipeline tested")
            
        except Exception as e:
            logger.error(f"❌ Phase 4 failed: {e}")
            raise

    async def _clear_database(self):
        """Clear all relevant tables in the database"""
        logger.info("🧹 Clearing database tables...")
        try:
            if not self.db:
                logger.error("❌ Cannot clear database, session not available")
                return
            
            self.db.query(ProcessedChat).delete()
            self.db.query(Message).delete()
            self.db.query(Conversation).delete()
            self.db.commit()
            logger.info("✅ Database tables cleared successfully")
        except Exception as e:
            logger.error(f"❌ Error clearing database: {e}")
            self.db.rollback()
            raise

async def main():
    """Main diagnostic runner"""
    diagnostic = BackendDiagnostic()
    await diagnostic.run_diagnostic()

if __name__ == "__main__":
    asyncio.run(main())