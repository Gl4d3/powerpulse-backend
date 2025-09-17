"""
Large Sample CSI Validation using Real Conversation Data

This test validates CSI calculation using real conversation data from the database
to ensure the methodology works correctly at scale and with realistic data patterns.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

from services.enhanced_analytics_service import EnhancedAnalyticsService
from models import DailyAnalysis

class RealDataCSIValidator:
    """CSI validation using real conversation data."""
    
    def __init__(self, db_path: str = "powerpulse.db"):
        self.db_path = db_path
        self.service = EnhancedAnalyticsService()
        
    def get_conversation_sample(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get a sample of conversations from the database."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT 
            c.id as conversation_id,
            c.customer_name,
            c.total_messages as message_count,
            c.first_message_time as start_time,
            c.last_message_time as end_time,
            CASE 
                WHEN c.total_messages > 0 
                THEN CAST(c.agent_messages AS FLOAT) / c.total_messages 
                ELSE 0 
            END as agent_response_ratio,
            -- Calculate basic timing metrics using social_create_time
            CASE 
                WHEN c.agent_messages > 0 
                THEN (julianday(MIN(CASE WHEN m.direction = 'to_client' THEN m.social_create_time END)) - 
                      julianday(c.first_message_time)) * 86400
                ELSE NULL 
            END as first_response_time_calc,
            -- Total conversation duration in minutes
            (julianday(c.last_message_time) - julianday(c.first_message_time)) * 1440 as duration_minutes
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        WHERE c.id IS NOT NULL 
        AND c.first_message_time IS NOT NULL
        AND c.total_messages >= 2  -- At least 2 messages for interaction
        GROUP BY c.id, c.customer_name, c.total_messages, c.agent_messages, c.first_message_time, c.last_message_time
        ORDER BY RANDOM()
        LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        
        return df.to_dict('records')
    
    def generate_realistic_metrics(self, conv: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic micro-metrics for a conversation."""
        np.random.seed(conv['conversation_id'])  # Consistent random generation
        
        # Base metrics on conversation characteristics
        message_count = conv['message_count']
        duration_mins = conv.get('duration_minutes', 0) or 0
        agent_ratio = conv.get('agent_response_ratio', 0.5) or 0.5
        
        # Generate metrics with realistic correlation
        # More messages and longer duration typically indicate more complex issues
        complexity_factor = min(1.0, (message_count - 2) / 10 + duration_mins / 60)
        
        # Effectiveness metrics (0-10 scale)
        # Complex conversations tend to have lower resolution
        base_resolution = max(2.0, 10.0 - complexity_factor * 6)
        resolution_achieved = max(0, min(10, np.random.normal(base_resolution, 2)))
        fcr_score = resolution_achieved * np.random.uniform(0.8, 1.2)  # Correlated with resolution
        
        # Effort (CES scale 1-7, then converted to 0-10)
        # Higher complexity = higher effort
        base_ces = min(7.0, 2.0 + complexity_factor * 4)
        ces = max(1, min(7, np.random.normal(base_ces, 1)))
        
        # Efficiency (time-based)
        # Use actual timing if available, otherwise generate realistic values
        first_response_time = conv.get('first_response_time_calc')
        if first_response_time is None or first_response_time < 0:
            # Generate realistic first response time (30 seconds to 2 hours)
            first_response_time = np.random.lognormal(np.log(300), 1.5)  # Log-normal distribution
        
        # Average response time (typically faster than first response)
        avg_response_time = first_response_time * np.random.uniform(0.3, 0.8)
        
        # Total handling time based on duration
        total_handling_time = max(1, duration_mins + np.random.normal(0, 10))
        
        # Empathy metrics
        # Sentiment typically improves for resolved issues
        base_sentiment = 3 + (resolution_achieved / 10) * 4  # 3-7 range
        sentiment_score = max(0, min(10, np.random.normal(base_sentiment, 1.5)))
        
        # Sentiment shift (improvement for resolved cases)
        if resolution_achieved > 7:
            sentiment_shift = np.random.uniform(0.5, 3.0)  # Positive shift
        elif resolution_achieved < 4:
            sentiment_shift = np.random.uniform(-3.0, -0.5)  # Negative shift
        else:
            sentiment_shift = np.random.uniform(-1.0, 1.0)  # Mixed
        
        return {
            'conversation_id': conv['conversation_id'],
            'sentiment_score': round(sentiment_score, 2),
            'sentiment_shift': round(sentiment_shift, 2),
            'resolution_achieved': round(resolution_achieved, 2),
            'fcr_score': round(fcr_score, 2),
            'ces': round(ces, 2),
            'first_response_time': round(first_response_time, 2),
            'avg_response_time': round(avg_response_time, 2),
            'total_handling_time': round(total_handling_time, 2),
            'message_count': message_count,
            'duration_minutes': duration_mins,
            'complexity_factor': round(complexity_factor, 2)
        }
    
    def validate_large_sample(self, sample_size: int = 200) -> Dict[str, Any]:
        """Validate CSI calculation on large sample of real conversations."""
        print(f"=== Large Sample CSI Validation (n={sample_size}) ===")
        
        # Get conversation sample
        conversations = self.get_conversation_sample(sample_size)
        print(f"Retrieved {len(conversations)} conversations from database")
        
        results = []
        processing_errors = []
        
        for conv in conversations:
            try:
                # Generate realistic metrics
                metrics = self.generate_realistic_metrics(conv)
                
                # Create analysis object (exclude non-model fields)
                model_fields = {
                    'sentiment_score': metrics['sentiment_score'],
                    'sentiment_shift': metrics['sentiment_shift'],
                    'resolution_achieved': metrics['resolution_achieved'],
                    'fcr_score': metrics['fcr_score'],
                    'ces': metrics['ces'],
                    'first_response_time': metrics['first_response_time'],
                    'avg_response_time': metrics['avg_response_time'],
                    'total_handling_time': metrics['total_handling_time']
                }
                
                analysis = DailyAnalysis(
                    conversation_id=metrics['conversation_id'],
                    analysis_date=datetime.now().date(),
                    **model_fields
                )
                
                # Calculate CSI
                self.service.calculate_and_set_csi_score(analysis)
                
                # Collect results
                result = {
                    'conversation_id': metrics['conversation_id'],
                    'csi_score': analysis.csi_score,
                    'effectiveness_score': analysis.effectiveness_score,
                    'effort_score': analysis.effort_score,
                    'efficiency_score': analysis.efficiency_score,
                    'empathy_score': analysis.empathy_score,
                    'message_count': metrics['message_count'],
                    'complexity_factor': metrics['complexity_factor'],
                    'input_metrics': metrics
                }
                
                results.append(result)
                
            except Exception as e:
                processing_errors.append({
                    'conversation_id': conv['conversation_id'],
                    'error': str(e)
                })
                print(f"Error processing conversation {conv['conversation_id']}: {str(e)}")
        
        # Analyze results
        return self.analyze_validation_results(results, processing_errors)
    
    def analyze_validation_results(self, results: List[Dict], errors: List[Dict]) -> Dict[str, Any]:
        """Analyze the validation results and generate comprehensive report."""
        
        # Basic statistics
        total_processed = len(results)
        error_count = len(errors)
        
        # CSI score analysis
        csi_scores = [r['csi_score'] for r in results if r['csi_score'] is not None]
        null_csi_count = len([r for r in results if r['csi_score'] is None])
        
        # Pillar score analysis
        effectiveness_scores = [r['effectiveness_score'] for r in results if r['effectiveness_score'] is not None]
        effort_scores = [r['effort_score'] for r in results if r['effort_score'] is not None]
        efficiency_scores = [r['efficiency_score'] for r in results if r['efficiency_score'] is not None]
        empathy_scores = [r['empathy_score'] for r in results if r['empathy_score'] is not None]
        
        # Data quality checks
        invalid_csi = [s for s in csi_scores if s < 0 or s > 10 or np.isnan(s) or not np.isfinite(s)]
        
        # Correlation analysis
        df_results = pd.DataFrame(results)
        correlations = {}
        if len(df_results) > 1:
            correlations = {
                'csi_vs_complexity': df_results[['csi_score', 'complexity_factor']].corr().iloc[0,1] if 'complexity_factor' in df_results.columns else None,
                'csi_vs_message_count': df_results[['csi_score', 'message_count']].corr().iloc[0,1] if 'message_count' in df_results.columns else None
            }
        
        # Generate comprehensive report
        report = {
            'sample_size': total_processed + error_count,
            'successfully_processed': total_processed,
            'processing_errors': error_count,
            'error_rate': (error_count / (total_processed + error_count)) * 100 if (total_processed + error_count) > 0 else 0,
            
            'csi_analysis': {
                'valid_csi_count': len(csi_scores),
                'null_csi_count': null_csi_count,
                'invalid_csi_count': len(invalid_csi),
                'csi_range': (min(csi_scores), max(csi_scores)) if csi_scores else None,
                'csi_mean': np.mean(csi_scores) if csi_scores else None,
                'csi_std': np.std(csi_scores) if csi_scores else None,
                'csi_percentiles': {
                    'p25': np.percentile(csi_scores, 25) if csi_scores else None,
                    'p50': np.percentile(csi_scores, 50) if csi_scores else None,
                    'p75': np.percentile(csi_scores, 75) if csi_scores else None,
                    'p90': np.percentile(csi_scores, 90) if csi_scores else None
                }
            },
            
            'pillar_analysis': {
                'effectiveness': {
                    'count': len(effectiveness_scores),
                    'mean': np.mean(effectiveness_scores) if effectiveness_scores else None,
                    'range': (min(effectiveness_scores), max(effectiveness_scores)) if effectiveness_scores else None
                },
                'effort': {
                    'count': len(effort_scores),
                    'mean': np.mean(effort_scores) if effort_scores else None,
                    'range': (min(effort_scores), max(effort_scores)) if effort_scores else None
                },
                'efficiency': {
                    'count': len(efficiency_scores),
                    'mean': np.mean(efficiency_scores) if efficiency_scores else None,
                    'range': (min(efficiency_scores), max(efficiency_scores)) if efficiency_scores else None
                },
                'empathy': {
                    'count': len(empathy_scores),
                    'mean': np.mean(empathy_scores) if empathy_scores else None,
                    'range': (min(empathy_scores), max(empathy_scores)) if empathy_scores else None
                }
            },
            
            'data_quality': {
                'all_scores_in_range': len(invalid_csi) == 0,
                'no_processing_errors': error_count == 0,
                'reasonable_null_rate': (null_csi_count / total_processed) < 0.1 if total_processed > 0 else False
            },
            
            'correlations': correlations,
            'sample_conversations': results[:5] if results else [],
            'errors': errors[:5] if errors else []
        }
        
        self.print_validation_report(report)
        return report
    
    def print_validation_report(self, report: Dict[str, Any]):
        """Print comprehensive validation report."""
        print("\n" + "="*80)
        print("LARGE SAMPLE CSI VALIDATION REPORT")
        print("="*80)
        
        print(f"\nSample Overview:")
        print(f"  Total Conversations: {report['sample_size']}")
        print(f"  Successfully Processed: {report['successfully_processed']}")
        print(f"  Processing Errors: {report['processing_errors']}")
        print(f"  Error Rate: {report['error_rate']:.2f}%")
        
        csi = report['csi_analysis']
        print(f"\nCSI Score Analysis:")
        print(f"  Valid CSI Scores: {csi['valid_csi_count']}")
        print(f"  Null CSI Scores: {csi['null_csi_count']}")
        print(f"  Invalid CSI Scores: {csi['invalid_csi_count']}")
        
        if csi['csi_range']:
            print(f"  CSI Range: {csi['csi_range'][0]:.2f} - {csi['csi_range'][1]:.2f}")
            print(f"  CSI Mean: {csi['csi_mean']:.2f} ± {csi['csi_std']:.2f}")
            print(f"  CSI Percentiles: P25={csi['csi_percentiles']['p25']:.2f}, P50={csi['csi_percentiles']['p50']:.2f}, P75={csi['csi_percentiles']['p75']:.2f}, P90={csi['csi_percentiles']['p90']:.2f}")
        
        print(f"\nPillar Score Analysis:")
        for pillar_name, pillar_data in report['pillar_analysis'].items():
            if pillar_data['mean'] is not None:
                print(f"  {pillar_name.title()}: {pillar_data['count']} scores, mean={pillar_data['mean']:.2f}, range={pillar_data['range'][0]:.2f}-{pillar_data['range'][1]:.2f}")
        
        print(f"\nData Quality Assessment:")
        quality = report['data_quality']
        print(f"  All scores in valid range (0-10): {'✓' if quality['all_scores_in_range'] else '✗'}")
        print(f"  No processing errors: {'✓' if quality['no_processing_errors'] else '✗'}")
        print(f"  Reasonable null rate (<10%): {'✓' if quality['reasonable_null_rate'] else '✗'}")
        
        if report['correlations']:
            print(f"\nCorrelation Analysis:")
            for corr_name, corr_value in report['correlations'].items():
                if corr_value is not None:
                    print(f"  {corr_name}: {corr_value:.3f}")
        
        # Overall validation status
        overall_pass = (
            quality['all_scores_in_range'] and
            quality['no_processing_errors'] and
            csi['valid_csi_count'] > 0 and
            csi['invalid_csi_count'] == 0
        )
        
        print(f"\nOverall Validation Status: {'✅ PASSED' if overall_pass else '❌ FAILED'}")
        
        return overall_pass

def main():
    """Run large sample CSI validation."""
    print("Starting Large Sample CSI Validation with Real Data...")
    
    validator = RealDataCSIValidator()
    
    # Test with different sample sizes
    sample_sizes = [50, 150, 300]
    
    all_results = []
    
    for sample_size in sample_sizes:
        print(f"\n{'='*50}")
        print(f"Testing with Sample Size: {sample_size}")
        print(f"{'='*50}")
        
        result = validator.validate_large_sample(sample_size)
        all_results.append({
            'sample_size': sample_size,
            'result': result
        })
    
    # Summary across all sample sizes
    print(f"\n" + "="*80)
    print("MULTI-SAMPLE VALIDATION SUMMARY")
    print("="*80)
    
    for test_result in all_results:
        sample_size = test_result['sample_size']
        result = test_result['result']
        
        success_rate = (result['successfully_processed'] / result['sample_size']) * 100
        valid_csi_rate = (result['csi_analysis']['valid_csi_count'] / result['successfully_processed']) * 100 if result['successfully_processed'] > 0 else 0
        
        mean_csi = result['csi_analysis']['csi_mean']
        mean_csi_str = f"{mean_csi:.2f}" if mean_csi is not None else "N/A"
        print(f"Sample Size {sample_size}: {success_rate:.1f}% processed, {valid_csi_rate:.1f}% valid CSI, Mean CSI={mean_csi_str}")
    
    print(f"\nLarge Sample CSI Validation Complete!")

if __name__ == "__main__":
    main()