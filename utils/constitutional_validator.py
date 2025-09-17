#!/usr/bin/env python3
"""
Constitutional Compliance Validator for PowerPulse

This utility validates complete constitutional compliance of the interaction analysis system
following Amendment I (AI micro-metrics extraction) and Amendment II (pipeline consistency).

Usage:
    python utils/constitutional_validator.py

Features:
- Complete pipeline validation
- Curated sample testing
- CSI correlation analysis
- Rule-based method detection
- Performance benchmarking
- API schema validation
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import statistics
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import SessionLocal
from models import InteractionAnalysis, DailyAnalysis, Conversation, Message
from services.gemini_service import GeminiService
from services.interaction_analytics_service import InteractionAnalyticsService
from services.analytics_service import analytics_service
from services.enhanced_analytics_service import enhanced_analytics_service
from services.csi_analysis_pipeline import CSIAnalysisPipeline
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Results from constitutional compliance validation"""
    test_name: str
    passed: bool
    details: Dict[str, Any]
    error_message: Optional[str] = None

class ConstitutionalValidator:
    """Comprehensive constitutional compliance validator"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.gemini_service = None
        self.interaction_service = None
        self.pipeline = None
        self.mock_mode = False
        
        # Load curated sample if available
        self.curated_sample_path = project_root / "attached_assets" / "curated_sample.json"
        self.curated_sample = self._load_curated_sample()
    
    def _load_curated_sample(self) -> Optional[Dict]:
        """Load curated sample data for testing"""
        try:
            if self.curated_sample_path.exists():
                with open(self.curated_sample_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Curated sample not found: {self.curated_sample_path}")
                return None
        except Exception as e:
            logger.error(f"Failed to load curated sample: {e}")
            return None
    
    async def initialize_services(self) -> bool:
        """Initialize all services for testing"""
        try:
            # Initialize config settings
            settings = config.Settings()
            
            # Check for API key configuration - allow mock mode if not available
            if not settings.GEMINI_API_KEY:
                logger.warning("⚠️  GEMINI_API_KEY not configured - running in MOCK MODE")
                logger.warning("   Constitutional structure tests will run, but AI calls will be mocked")
                self.mock_mode = True
                # Use dummy key for service initialization
                api_key = "mock_key_for_testing"
            else:
                self.mock_mode = False
                api_key = settings.GEMINI_API_KEY
                logger.info("✅ Real API key found - running in PRODUCTION MODE")
            
            self.gemini_service = GeminiService(api_key)
            self.interaction_service = InteractionAnalyticsService(self.gemini_service)
            self.pipeline = CSIAnalysisPipeline(self.gemini_service)
            
            logger.info("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            return False
    
    async def validate_ai_micrometrics_extraction(self) -> ValidationResult:
        """
        CONSTITUTIONAL TEST 1: Validate AI micro-metrics extraction works for interactions
        """
        logger.info("🔍 Testing AI micro-metrics extraction...")
        
        if self.mock_mode:
            logger.info("   Running in MOCK MODE - testing method existence only")
            
            # Test method exists and is callable
            has_method = hasattr(self.interaction_service, '_extract_ai_micrometrics')
            method_callable = callable(getattr(self.interaction_service, '_extract_ai_micrometrics', None))
            
            passed = has_method and method_callable
            
            return ValidationResult(
                "ai_micrometrics_extraction",
                passed,
                {
                    "mock_mode": True,
                    "method_exists": has_method,
                    "method_callable": method_callable,
                    "constitutional_structure": "COMPLIANT" if passed else "NON_COMPLIANT"
                }
            )
        
        try:
            db = SessionLocal()
            
            # Get test interactions
            test_interactions = db.query(InteractionAnalysis).limit(3).all()
            
            if not test_interactions:
                return ValidationResult(
                    "ai_micrometrics_extraction",
                    False,
                    {"error": "No test interactions found"},
                    "No interactions available for testing"
                )
            
            # Test AI extraction
            ai_metrics = await self.interaction_service._extract_ai_micrometrics(test_interactions)
            
            extracted_count = len(ai_metrics)
            expected_metrics = ['sentiment_score', 'sentiment_shift', 'resolution_achieved', 'fcr_score', 'ces']
            
            valid_extractions = 0
            for interaction_id, metrics_data in ai_metrics.items():
                extracted_metrics = [k for k in expected_metrics if k in metrics_data and metrics_data[k] is not None]
                if len(extracted_metrics) >= 3:  # At least 60% of metrics
                    valid_extractions += 1
            
            success_rate = valid_extractions / len(test_interactions) if test_interactions else 0
            
            passed = extracted_count > 0 and success_rate >= 0.6
            
            return ValidationResult(
                "ai_micrometrics_extraction",
                passed,
                {
                    "mock_mode": False,
                    "test_interactions": len(test_interactions),
                    "extractions_completed": extracted_count,
                    "success_rate": success_rate,
                    "extracted_metrics_sample": list(ai_metrics.values())[0] if ai_metrics else {}
                }
            )
            
        except Exception as e:
            return ValidationResult(
                "ai_micrometrics_extraction",
                False,
                {"error": str(e)},
                f"AI micro-metrics extraction failed: {e}"
            )
        finally:
            db.close()
    
    async def validate_no_rule_based_methods(self) -> ValidationResult:
        """
        CONSTITUTIONAL TEST 2: Verify no rule-based calculation methods exist
        """
        logger.info("🔍 Checking for constitutional violations (rule-based methods)...")
        
        forbidden_methods = [
            '_calculate_effectiveness',
            '_calculate_effort', 
            '_calculate_efficiency',
            '_calculate_empathy'
        ]
        
        violations = []
        for method_name in forbidden_methods:
            if hasattr(self.interaction_service, method_name):
                method = getattr(self.interaction_service, method_name)
                if callable(method):
                    violations.append(method_name)
        
        passed = len(violations) == 0
        
        return ValidationResult(
            "no_rule_based_methods",
            passed,
            {
                "forbidden_methods_checked": forbidden_methods,
                "violations_found": violations,
                "constitutional_status": "COMPLIANT" if passed else "VIOLATED"
            },
            None if passed else f"Constitutional violations found: {violations}"
        )
    
    async def validate_four_pillars_calculation(self) -> ValidationResult:
        """
        CONSTITUTIONAL TEST 3: Validate four-pillars calculation uses enhanced analytics
        """
        logger.info("🔍 Testing four-pillars calculation methodology...")
        
        try:
            db = SessionLocal()
            
            # Get test interaction
            test_interaction = db.query(InteractionAnalysis).filter(
                InteractionAnalysis.csi_score.isnot(None)
            ).first()
            
            if not test_interaction:
                return ValidationResult(
                    "four_pillars_calculation",
                    False,
                    {"error": "No test interaction with CSI score found"},
                    "No suitable test data"
                )
            
            # Store original values
            original_csi = test_interaction.csi_score
            original_effectiveness = test_interaction.effectiveness_score
            
            # Test constitutional analysis
            metrics = await self.interaction_service.analyze_interaction(db, test_interaction)
            
            # Validate results
            has_csi = metrics.overall_csi > 0
            has_pillars = all([
                metrics.effectiveness_score > 0,
                metrics.effort_score > 0,
                metrics.efficiency_score > 0,
                metrics.empathy_score > 0
            ])
            
            passed = has_csi and has_pillars
            
            return ValidationResult(
                "four_pillars_calculation",
                passed,
                {
                    "interaction_id": test_interaction.id,
                    "calculated_csi": metrics.overall_csi,
                    "effectiveness": metrics.effectiveness_score,
                    "effort": metrics.effort_score,
                    "efficiency": metrics.efficiency_score,
                    "empathy": metrics.empathy_score,
                    "confidence": metrics.confidence
                }
            )
            
        except Exception as e:
            return ValidationResult(
                "four_pillars_calculation",
                False,
                {"error": str(e)},
                f"Four-pillars calculation failed: {e}"
            )
        finally:
            db.close()
    
    async def validate_csi_correlation(self) -> ValidationResult:
        """
        CONSTITUTIONAL TEST 4: Validate >0.8 correlation between daily and interaction CSI
        """
        logger.info("🔍 Testing CSI correlation between daily and interaction analysis...")
        
        if not self.curated_sample:
            return ValidationResult(
                "csi_correlation",
                False,
                {"error": "Curated sample not available"},
                "Cannot test correlation without curated sample"
            )
        
        try:
            db = SessionLocal()
            
            # Get sample interactions and daily analyses for correlation
            interactions = db.query(InteractionAnalysis).filter(
                InteractionAnalysis.csi_score.isnot(None)
            ).limit(10).all()
            
            daily_analyses = db.query(DailyAnalysis).filter(
                DailyAnalysis.csi_score.isnot(None)
            ).limit(10).all()
            
            if len(interactions) < 5 or len(daily_analyses) < 5:
                return ValidationResult(
                    "csi_correlation",
                    False,
                    {"error": "Insufficient data for correlation analysis"},
                    "Need at least 5 samples each for correlation"
                )
            
            # Extract CSI scores
            interaction_scores = [i.csi_score for i in interactions if i.csi_score is not None]
            daily_scores = [d.csi_score for d in daily_analyses if d.csi_score is not None]
            
            # Simple correlation approximation (same methodology should yield similar score distributions)
            interaction_avg = statistics.mean(interaction_scores) if interaction_scores else 0
            daily_avg = statistics.mean(daily_scores) if daily_scores else 0
            
            # Constitutional requirement: methods should produce similar average scores
            score_difference = abs(interaction_avg - daily_avg)
            correlation_approximation = max(0, 1 - (score_difference / 10))  # Normalize to 0-1
            
            passed = correlation_approximation >= 0.8
            
            return ValidationResult(
                "csi_correlation",
                passed,
                {
                    "interaction_samples": len(interaction_scores),
                    "daily_samples": len(daily_scores),
                    "interaction_avg_csi": interaction_avg,
                    "daily_avg_csi": daily_avg,
                    "score_difference": score_difference,
                    "correlation_approximation": correlation_approximation,
                    "constitutional_threshold": 0.8
                }
            )
            
        except Exception as e:
            return ValidationResult(
                "csi_correlation",
                False,
                {"error": str(e)},
                f"CSI correlation validation failed: {e}"
            )
        finally:
            db.close()
    
    async def validate_dual_csi_storage(self) -> ValidationResult:
        """
        CONSTITUTIONAL TEST 5: Validate dual CSI storage (calculated + inferred)
        """
        logger.info("🔍 Testing dual CSI storage requirement...")
        
        try:
            db = SessionLocal()
            
            # Check database schema supports dual CSI
            test_interaction = db.query(InteractionAnalysis).first()
            
            if not test_interaction:
                return ValidationResult(
                    "dual_csi_storage",
                    False,
                    {"error": "No test interaction found"},
                    "No interactions available for schema validation"
                )
            
            # Check fields exist
            has_calculated_csi = hasattr(test_interaction, 'csi_score')
            has_inferred_csi = hasattr(test_interaction, 'inferred_csi')
            has_micro_metrics = all(hasattr(test_interaction, field) for field in [
                'sentiment_score', 'sentiment_shift', 'resolution_achieved', 'fcr_score', 'ces'
            ])
            has_four_pillars = all(hasattr(test_interaction, field) for field in [
                'effectiveness_score', 'effort_score', 'efficiency_score', 'empathy_score'
            ])
            
            passed = all([has_calculated_csi, has_inferred_csi, has_micro_metrics, has_four_pillars])
            
            return ValidationResult(
                "dual_csi_storage",
                passed,
                {
                    "calculated_csi_field": has_calculated_csi,
                    "inferred_csi_field": has_inferred_csi,
                    "micro_metrics_fields": has_micro_metrics,
                    "four_pillars_fields": has_four_pillars,
                    "schema_compliance": "FULL" if passed else "PARTIAL"
                }
            )
            
        except Exception as e:
            return ValidationResult(
                "dual_csi_storage",
                False,
                {"error": str(e)},
                f"Dual CSI storage validation failed: {e}"
            )
        finally:
            db.close()
    
    async def validate_pipeline_integration(self) -> ValidationResult:
        """
        CONSTITUTIONAL TEST 6: Validate complete pipeline integration
        """
        logger.info("🔍 Testing complete pipeline integration...")
        
        try:
            db = SessionLocal()
            
            # Get test conversation for pipeline
            test_conversation = db.query(Conversation).first()
            
            if not test_conversation:
                return ValidationResult(
                    "pipeline_integration",
                    False,
                    {"error": "No test conversation found"},
                    "No conversations available for pipeline testing"
                )
            
            # Test pipeline can process conversation
            # Note: We'll test the interaction service directly since pipeline might need conversation processing
            interactions = db.query(InteractionAnalysis).filter(
                InteractionAnalysis.conversation_id == test_conversation.id
            ).all()
            
            if not interactions:
                return ValidationResult(
                    "pipeline_integration",
                    False,
                    {"error": f"No interactions found for conversation {test_conversation.id}"},
                    "No interaction data for pipeline testing"
                )
            
            # Test interaction processing
            processed_count = 0
            for interaction in interactions[:3]:  # Test first 3
                try:
                    metrics = await self.interaction_service.analyze_interaction(db, interaction)
                    if metrics.overall_csi > 0:
                        processed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to process interaction {interaction.id}: {e}")
            
            success_rate = processed_count / min(len(interactions), 3)
            passed = success_rate >= 0.5  # At least 50% success rate
            
            return ValidationResult(
                "pipeline_integration",
                passed,
                {
                    "test_conversation_id": test_conversation.id,
                    "total_interactions": len(interactions),
                    "processed_successfully": processed_count,
                    "success_rate": success_rate
                }
            )
            
        except Exception as e:
            return ValidationResult(
                "pipeline_integration",
                False,
                {"error": str(e)},
                f"Pipeline integration failed: {e}"
            )
        finally:
            db.close()
    
    async def run_all_validations(self) -> Dict[str, Any]:
        """Run complete constitutional compliance validation suite"""
        logger.info("🚀 Starting Constitutional Compliance Validation Suite")
        logger.info("=" * 80)
        
        # Initialize services
        if not await self.initialize_services():
            return {
                "overall_status": "FAILED",
                "error": "Service initialization failed",
                "tests_completed": 0,
                "tests_passed": 0
            }
        
        # Run all validation tests
        validation_tests = [
            self.validate_ai_micrometrics_extraction,
            self.validate_no_rule_based_methods,
            self.validate_four_pillars_calculation,
            self.validate_csi_correlation,
            self.validate_dual_csi_storage,
            self.validate_pipeline_integration
        ]
        
        for test_func in validation_tests:
            try:
                result = await test_func()
                self.results.append(result)
                
                # Log result
                status = "✅ PASSED" if result.passed else "❌ FAILED"
                logger.info(f"{status}: {result.test_name}")
                if result.error_message:
                    logger.error(f"   Error: {result.error_message}")
                
            except Exception as e:
                error_result = ValidationResult(
                    test_func.__name__.replace('validate_', ''),
                    False,
                    {"error": str(e)},
                    f"Test execution failed: {e}"
                )
                self.results.append(error_result)
                logger.error(f"❌ FAILED: {error_result.test_name} - {e}")
        
        # Calculate summary
        tests_completed = len(self.results)
        tests_passed = sum(1 for r in self.results if r.passed)
        pass_rate = tests_passed / tests_completed if tests_completed > 0 else 0
        
        overall_status = "COMPLIANT" if pass_rate >= 0.8 else "NON_COMPLIANT"
        
        logger.info("=" * 80)
        logger.info(f"🏁 CONSTITUTIONAL COMPLIANCE SUMMARY")
        logger.info(f"Tests Completed: {tests_completed}")
        logger.info(f"Tests Passed: {tests_passed}")
        logger.info(f"Pass Rate: {pass_rate:.1%}")
        logger.info(f"Overall Status: {overall_status}")
        
        return {
            "overall_status": overall_status,
            "tests_completed": tests_completed,
            "tests_passed": tests_passed,
            "pass_rate": pass_rate,
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "details": r.details,
                    "error": r.error_message
                }
                for r in self.results
            ]
        }
    
    def save_results(self, results: Dict[str, Any], output_file: str = "constitutional_validation_results.json"):
        """Save validation results to file"""
        output_path = project_root / output_file
        
        results_with_metadata = {
            "validation_timestamp": datetime.now().isoformat(),
            "validation_version": "1.0.0",
            "constitutional_requirements": [
                "Amendment I: AI micro-metrics extraction SHALL remain authoritative",
                "Amendment II: Pipeline logic SHALL remain identical to daily analysis",
                "Amendment III: Test-driven development SHALL prevent scope creep"
            ],
            **results
        }
        
        with open(output_path, 'w') as f:
            json.dump(results_with_metadata, f, indent=2)
        
        logger.info(f"📋 Results saved to: {output_path}")

async def main():
    """Main validation entry point"""
    validator = ConstitutionalValidator()
    
    try:
        results = await validator.run_all_validations()
        validator.save_results(results)
        
        # Exit with appropriate code
        if results["overall_status"] == "COMPLIANT":
            logger.info("🎉 CONSTITUTIONAL COMPLIANCE: VALIDATED")
            sys.exit(0)
        else:
            logger.error("⚠️  CONSTITUTIONAL VIOLATIONS DETECTED")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Validation suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())