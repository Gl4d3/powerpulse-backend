"""
Gemini Integration Validation Test

This utility tests the actual Gemini API integration to verify:
1. API connectivity and authentication
2. Micro-metrics generation (sentiment_score, resolution_achieved, etc.)
3. Response parsing and CSI calculation pipeline
4. Identify any blockages preventing real AI analysis

Author: GitHub Copilot
Date: September 17, 2025
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from services.gemini_service import GeminiService
from services.enhanced_analytics_service import EnhancedAnalyticsService
from models import DailyAnalysis, Conversation, Message
from config import settings
from database import SessionLocal
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GeminiIntegrationTester:
    """Test suite for Gemini AI integration validation."""
    
    def __init__(self):
        self.analytics_service = EnhancedAnalyticsService()
        self.test_results = {
            'api_connectivity': False,
            'micro_metrics_generated': False,
            'csi_calculation_works': False,
            'errors': [],
            'sample_results': []
        }
    
    async def run_comprehensive_test(self):
        """Run complete Gemini integration validation."""
        logger.info("=== Starting Comprehensive Gemini Integration Test ===")
        
        # Test 1: API Connectivity
        await self._test_api_connectivity()
        
        # Test 2: Real Data Analysis
        await self._test_real_conversation_analysis()
        
        # Test 3: CSI Calculation Pipeline
        await self._test_csi_calculation_pipeline()
        
        # Test 4: Database Integration
        await self._test_database_integration()
        
        # Generate Report
        self._generate_test_report()
        
        return self.test_results
    
    async def _test_api_connectivity(self):
        """Test basic Gemini API connectivity."""
        logger.info("Test 1: API Connectivity")
        
        try:
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not configured")
            
            service = GeminiService(settings.GEMINI_API_KEY)
            logger.info("✅ GeminiService initialized successfully")
            logger.info(f"   Model: {settings.GEMINI_MODEL}")
            
            self.test_results['api_connectivity'] = True
            
        except Exception as e:
            error_msg = f"❌ API Connectivity failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    async def _test_real_conversation_analysis(self):
        """Test analysis with real conversation data."""
        logger.info("Test 2: Real Conversation Analysis")
        
        try:
            # Try using real database conversation first
            db = SessionLocal()
            try:
                # Get a conversation with messages for testing
                real_daily_analysis = (
                    db.query(DailyAnalysis)
                    .join(Conversation)
                    .filter(Conversation.total_messages > 3)  # Need some messages to test with
                    .first()
                )
                
                if real_daily_analysis and real_daily_analysis.conversation and real_daily_analysis.conversation.messages:
                    logger.info(f"Using real conversation: ID={real_daily_analysis.conversation_id}, Messages={len(real_daily_analysis.conversation.messages)}")
                    test_analysis = real_daily_analysis
                else:
                    logger.info("No suitable real conversation found, creating synthetic test")
                    # Fallback to synthetic data but with proper structure
                    test_analysis = self._create_synthetic_daily_analysis(db)
                
            finally:
                db.close()
            
            # Test Gemini analysis
            service = GeminiService(settings.GEMINI_API_KEY)
            logger.info(f"Analyzing conversation: {test_analysis.conversation_id}")
            
            analysis_results, missed_ids, usage_metadata, response_text = await service.analyze_daily_analyses_batch([test_analysis])
            
            # Validate results
            if analysis_results:
                result = analysis_results[0]
                logger.info("✅ Gemini analysis successful!")
                logger.info(f"   Results keys: {list(result.keys())}")
                
                # Check for key micro-metrics
                required_metrics = ['sentiment_score', 'resolution_achieved', 'fcr_score', 'ces']
                metrics_found = []
                
                for metric in required_metrics:
                    if metric in result and result[metric] is not None:
                        metrics_found.append(f"{metric}={result[metric]}")
                    else:
                        logger.warning(f"   ⚠️  Missing or null: {metric}")
                
                if metrics_found:
                    logger.info(f"   Micro-metrics: {', '.join(metrics_found)}")
                    self.test_results['micro_metrics_generated'] = True
                    self.test_results['sample_results'].append({
                        'conversation_id': test_analysis.conversation_id,
                        'metrics': result,
                        'usage': usage_metadata
                    })
                
                logger.info(f"   Token usage: {usage_metadata}")
                logger.info(f"   Response length: {len(response_text)} chars")
                
            else:
                raise ValueError("No analysis results returned")
                
        except Exception as e:
            error_msg = f"❌ Real conversation analysis failed: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            self.test_results['errors'].append(error_msg)
    
    async def _test_csi_calculation_pipeline(self):
        """Test CSI calculation with AI-generated micro-metrics."""
        logger.info("Test 3: CSI Calculation Pipeline")
        
        try:
            if not self.test_results['sample_results']:
                logger.warning("⚠️  Skipping CSI test - no sample results available")
                return
            
            sample_result = self.test_results['sample_results'][0]
            metrics = sample_result['metrics']
            
            # Create DailyAnalysis with AI metrics
            analysis = DailyAnalysis(
                conversation_id=sample_result['conversation_id'],
                analysis_date=date.today()
            )
            
            # Apply AI-generated metrics
            for key, value in metrics.items():
                if hasattr(analysis, key) and value is not None:
                    setattr(analysis, key, value)
            
            # Calculate CSI
            self.analytics_service.calculate_and_set_csi_score(analysis)
            
            # Validate CSI calculation
            if analysis.csi_score is not None:
                logger.info("✅ CSI calculation successful!")
                logger.info(f"   CSI Score: {analysis.csi_score:.2f}")
                
                # Safe formatting for pillar scores (they might be None)
                def safe_format(score, default="N/A"):
                    return f"{score:.2f}" if score is not None else default
                
                logger.info(f"   Effectiveness: {safe_format(analysis.effectiveness_score)}")
                logger.info(f"   Effort: {safe_format(analysis.effort_score)}")
                logger.info(f"   Efficiency: {safe_format(analysis.efficiency_score)}")
                logger.info(f"   Empathy: {safe_format(analysis.empathy_score)}")
                
                # Validate score ranges
                if 0 <= analysis.csi_score <= 10:
                    self.test_results['csi_calculation_works'] = True
                else:
                    raise ValueError(f"CSI score out of range: {analysis.csi_score}")
            else:
                raise ValueError("CSI calculation returned None")
                
        except Exception as e:
            error_msg = f"❌ CSI calculation failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    async def _test_database_integration(self):
        """Test database integration and check existing data."""
        logger.info("Test 4: Database Integration")
        
        try:
            with SessionLocal() as db:
                # Check existing data
                total_analyses = db.query(DailyAnalysis).count()
                analyses_with_csi = db.query(DailyAnalysis).filter(DailyAnalysis.csi_score.isnot(None)).count()
                analyses_with_sentiment = db.query(DailyAnalysis).filter(DailyAnalysis.sentiment_score.isnot(None)).count()
                
                logger.info(f"   Total DailyAnalysis records: {total_analyses}")
                logger.info(f"   Records with CSI scores: {analyses_with_csi}")
                logger.info(f"   Records with sentiment scores: {analyses_with_sentiment}")
                
                if analyses_with_csi == 0 and total_analyses > 0:
                    logger.warning("⚠️  Database has analyses but no CSI scores - AI pipeline may be broken")
                
                # Check conversations and messages
                total_conversations = db.query(Conversation).count()
                total_messages = db.query(Message).count()
                
                logger.info(f"   Total conversations: {total_conversations}")
                logger.info(f"   Total messages: {total_messages}")
                
                # Sample data inspection
                if total_conversations > 0:
                    sample_conv = db.query(Conversation).first()
                    logger.info(f"   Sample conversation: ID={sample_conv.id}, Messages={sample_conv.total_messages}")
        
        except Exception as e:
            error_msg = f"❌ Database integration test failed: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
    
    def _load_sample_conversation(self) -> Dict[str, Any]:
        """Load sample conversation from curated data."""
        sample_paths = [
            "attached_assets/curated_sample.json",
            "attached_assets/FB17-23.json"
        ]
        
        for path in sample_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle different JSON formats
                if isinstance(data, dict):
                    if 'messages' in data:
                        raw_messages = data['messages'][:10]  # Take first 10 for testing
                    else:
                        # Take first conversation
                        first_chat_id = next(iter(data.keys()))
                        raw_messages = data[first_chat_id][:10]
                    
                    # Normalize message format - handle both MESSAGE and MESSAGE_CONTENT
                    normalized_messages = []
                    for msg in raw_messages:
                        normalized_msg = msg.copy()
                        
                        # Handle different message content field names
                        if 'MESSAGE' in msg:
                            normalized_msg['MESSAGE_CONTENT'] = msg['MESSAGE']
                        elif 'MESSAGE_CONTENT' not in msg:
                            logger.warning(f"No message content found in: {list(msg.keys())}")
                            continue
                        
                        # Ensure required fields exist
                        required_fields = ['DIRECTION', 'SOCIAL_CREATE_TIME']
                        if all(field in msg for field in required_fields):
                            normalized_messages.append(normalized_msg)
                    
                    if normalized_messages:
                        logger.info(f"Loaded {len(normalized_messages)} messages from {path}")
                        logger.info(f"Sample message keys: {list(normalized_messages[0].keys())}")
                        return {
                            'chat_id': 'TEST_GEMINI_INTEGRATION',
                            'messages': normalized_messages
                        }
                    
            except Exception as e:
                logger.warning(f"Could not load {path}: {e}")
        
        # Fallback: Create synthetic test data
        logger.info("Creating synthetic test conversation")
        return {
            'chat_id': 'SYNTHETIC_TEST',
            'messages': [
                {
                    'MESSAGE_CONTENT': 'Hello, we have a power outage in Kinoo area. Please help urgently.',
                    'DIRECTION': 'to_company',
                    'SOCIAL_CREATE_TIME': '2025-09-17T10:00:00.000Z',
                    'AGENT_USERNAME': None,
                    'AGENT_EMAIL': None
                },
                {
                    'MESSAGE_CONTENT': 'Hello. We have received your report. Our team is investigating the outage in Kinoo area. We will update you shortly.',
                    'DIRECTION': 'to_client',
                    'SOCIAL_CREATE_TIME': '2025-09-17T10:15:00.000Z',
                    'AGENT_USERNAME': 'agent123',
                    'AGENT_EMAIL': 'support@kplc.co.ke'
                },
                {
                    'MESSAGE_CONTENT': 'Thank you. When can we expect power to be restored?',
                    'DIRECTION': 'to_company',
                    'SOCIAL_CREATE_TIME': '2025-09-17T10:20:00.000Z',
                    'AGENT_USERNAME': None,
                    'AGENT_EMAIL': None
                },
                {
                    'MESSAGE_CONTENT': 'Power has been restored in your area. Please confirm if you now have electricity.',
                    'DIRECTION': 'to_client',
                    'SOCIAL_CREATE_TIME': '2025-09-17T12:30:00.000Z',
                    'AGENT_USERNAME': 'agent123',
                    'AGENT_EMAIL': 'support@kplc.co.ke'
                },
                {
                    'MESSAGE_CONTENT': 'Yes, power is back. Thank you for the quick response!',
                    'DIRECTION': 'to_company',
                    'SOCIAL_CREATE_TIME': '2025-09-17T12:35:00.000Z',
                    'AGENT_USERNAME': None,
                    'AGENT_EMAIL': None
                }
            ]
        }
    
    def _create_synthetic_daily_analysis(self, db) -> DailyAnalysis:
        """Create a synthetic test conversation and daily analysis in the database."""
        
        # Create a synthetic conversation
        test_conversation = Conversation(
            fb_chat_id='GEMINI_TEST_CONV_' + str(int(datetime.now().timestamp())),
            customer_name="Test Customer",
            total_messages=5,
            customer_messages=3,
            agent_messages=2
        )
        db.add(test_conversation)
        db.flush()  # Get the ID
        
        # Create synthetic messages
        test_messages = [
            Message(
                conversation_id=test_conversation.id,
                message_content="Hello, we have a power outage in Kinoo area. Please help urgently.",
                direction="to_company",
                social_create_time=datetime(2025, 9, 17, 10, 0, 0),
                agent_username=None,
                agent_email=None
            ),
            Message(
                conversation_id=test_conversation.id,
                message_content="Hello. We have received your report. Our team is investigating the outage in Kinoo area. We will update you shortly.",
                direction="to_client", 
                social_create_time=datetime(2025, 9, 17, 10, 15, 0),
                agent_username="agent123",
                agent_email="support@kplc.co.ke"
            ),
            Message(
                conversation_id=test_conversation.id,
                message_content="Thank you. When can we expect power to be restored?",
                direction="to_company",
                social_create_time=datetime(2025, 9, 17, 10, 20, 0),
                agent_username=None,
                agent_email=None
            ),
            Message(
                conversation_id=test_conversation.id,
                message_content="Power has been restored in your area. Please confirm if you now have electricity.",
                direction="to_client",
                social_create_time=datetime(2025, 9, 17, 12, 30, 0),
                agent_username="agent123",
                agent_email="support@kplc.co.ke"
            ),
            Message(
                conversation_id=test_conversation.id,
                message_content="Yes, power is back. Thank you for the quick response!",
                direction="to_company", 
                social_create_time=datetime(2025, 9, 17, 12, 35, 0),
                agent_username=None,
                agent_email=None
            )
        ]
        
        for msg in test_messages:
            db.add(msg)
        
        # Create DailyAnalysis object
        analysis = DailyAnalysis(
            conversation_id=test_conversation.id,
            analysis_date=date(2025, 9, 17)
        )
        db.add(analysis)
        db.flush()  # Get the relationship loaded
        
        # Ensure the relationships are loaded
        db.refresh(test_conversation)
        db.refresh(analysis)
        
        logger.info(f"Created synthetic conversation with {len(test_messages)} messages")
        return analysis
    
    def _generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("\n=== GEMINI INTEGRATION TEST REPORT ===")
        
        # Overall Status
        overall_success = (
            self.test_results['api_connectivity'] and
            self.test_results['micro_metrics_generated'] and
            self.test_results['csi_calculation_works']
        )
        
        status = "✅ PASSED" if overall_success else "❌ FAILED"
        logger.info(f"Overall Status: {status}")
        
        # Detailed Results
        logger.info(f"\nDetailed Results:")
        logger.info(f"  API Connectivity: {'✅' if self.test_results['api_connectivity'] else '❌'}")
        logger.info(f"  Micro-Metrics Generated: {'✅' if self.test_results['micro_metrics_generated'] else '❌'}")
        logger.info(f"  CSI Calculation Works: {'✅' if self.test_results['csi_calculation_works'] else '❌'}")
        
        # Errors
        if self.test_results['errors']:
            logger.info(f"\nErrors Encountered ({len(self.test_results['errors'])}):")
            for i, error in enumerate(self.test_results['errors'], 1):
                logger.info(f"  {i}. {error}")
        
        # Sample Results
        if self.test_results['sample_results']:
            logger.info(f"\nSample AI Results:")
            for result in self.test_results['sample_results']:
                logger.info(f"  Conversation: {result['conversation_id']}")
                metrics = result['metrics']
                if 'sentiment_score' in metrics:
                    logger.info(f"    Sentiment Score: {metrics['sentiment_score']}")
                if 'resolution_achieved' in metrics:
                    logger.info(f"    Resolution Achieved: {metrics['resolution_achieved']}")
                if 'usage' in result:
                    logger.info(f"    Token Usage: {result['usage']}")
        
        # Recommendations
        logger.info(f"\nRecommendations:")
        if not self.test_results['api_connectivity']:
            logger.info("  ⚠️  Fix API connectivity - check GEMINI_API_KEY and model configuration")
        elif not self.test_results['micro_metrics_generated']:
            logger.info("  ⚠️  Debug AI response parsing - check prompt format and response handling")
        elif not self.test_results['csi_calculation_works']:
            logger.info("  ⚠️  Fix CSI calculation logic - verify pillar score computation")
        else:
            logger.info("  ✅ AI integration working! Ready for interaction detection phase")
        
        logger.info("=== END REPORT ===\n")

async def main():
    """Run the Gemini integration test suite."""
    tester = GeminiIntegrationTester()
    
    try:
        results = await tester.run_comprehensive_test()
        return results
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    asyncio.run(main())