"""
Debug CSI Calculation Issue

The comprehensive test showed that final CSI calculations are returning None
when they should return values. Let's debug this step by step.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from services.enhanced_analytics_service import EnhancedAnalyticsService, CSI_PILLAR_WEIGHTS
from models import DailyAnalysis
from datetime import datetime

def debug_csi_calculation():
    service = EnhancedAnalyticsService()
    
    print("=== Debugging CSI Calculation Issue ===")
    
    # Create a test case with perfect scores
    analysis = DailyAnalysis(
        conversation_id=1,
        analysis_date=datetime.now().date(),
        sentiment_score=8.0,  # For empathy
        sentiment_shift=2.0,  # For empathy
        resolution_achieved=10.0,  # For effectiveness
        fcr_score=10.0,  # For effectiveness
        ces=7.0,  # For effort
        first_response_time=60,  # For efficiency
        avg_response_time=30,  # For efficiency
        total_handling_time=5  # For efficiency
    )
    
    print("Input metrics:")
    print(f"  sentiment_score: {analysis.sentiment_score}")
    print(f"  sentiment_shift: {analysis.sentiment_shift}")
    print(f"  resolution_achieved: {analysis.resolution_achieved}")
    print(f"  fcr_score: {analysis.fcr_score}")
    print(f"  ces: {analysis.ces}")
    print(f"  first_response_time: {analysis.first_response_time}")
    print(f"  avg_response_time: {analysis.avg_response_time}")
    print(f"  total_handling_time: {analysis.total_handling_time}")
    
    # Step through calculation
    print("\nStep 1: Calculate pillar scores")
    
    # Manually calculate each pillar to see intermediate steps
    # Effectiveness
    effectiveness = (analysis.resolution_achieved + analysis.fcr_score) / 2 if analysis.resolution_achieved is not None and analysis.fcr_score is not None else None
    print(f"  effectiveness (manual): {effectiveness}")
    
    # Effort
    effort = ((analysis.ces - 1) / 6) * 10 if analysis.ces is not None else None
    print(f"  effort (manual): {effort}")
    
    # Efficiency - this is complex
    def scale_time(value, max_time):
        if value is None or value < 0:
            return None
        capped_value = min(value, max_time * 3.0)
        normalized = capped_value / max_time
        efficiency_score = max(0, (1 - normalized)) * 10
        return min(10.0, max(0.0, efficiency_score))
    
    first_resp_score = scale_time(analysis.first_response_time, 3600)
    avg_resp_score = scale_time(analysis.avg_response_time, 1800)
    handling_score = scale_time(analysis.total_handling_time * 60, 7200)
    
    print(f"  efficiency components: first_resp={first_resp_score}, avg_resp={avg_resp_score}, handling={handling_score}")
    
    efficiency_scores = [first_resp_score, avg_resp_score, handling_score]
    valid_efficiency = [s for s in efficiency_scores if s is not None]
    efficiency = sum(valid_efficiency) / len(valid_efficiency) if valid_efficiency else None
    print(f"  efficiency (manual): {efficiency}")
    
    # Empathy
    normalized_shift = (analysis.sentiment_shift + 5) if analysis.sentiment_shift is not None else None
    empathy_scores = [analysis.sentiment_score, normalized_shift]
    valid_empathy = [s for s in empathy_scores if s is not None]
    empathy = sum(valid_empathy) / len(valid_empathy) if valid_empathy else None
    print(f"  empathy (manual): {empathy} (sentiment={analysis.sentiment_score}, norm_shift={normalized_shift})")
    
    # Now call the actual service method
    print(f"\nStep 2: Call service.calculate_and_set_csi_score()")
    service.calculate_and_set_csi_score(analysis)
    
    print("Pillar scores after calculation:")
    print(f"  effectiveness_score: {analysis.effectiveness_score}")
    print(f"  effort_score: {analysis.effort_score}")
    print(f"  efficiency_score: {analysis.efficiency_score}")
    print(f"  empathy_score: {analysis.empathy_score}")
    
    # Check final CSI calculation
    print(f"\nStep 3: Final CSI calculation")
    pillar_scores = {
        'effectiveness': analysis.effectiveness_score,
        'effort': analysis.effort_score,
        'efficiency': analysis.efficiency_score,
        'empathy': analysis.empathy_score
    }
    
    valid_pillars = {k: v for k, v in pillar_scores.items() if v is not None}
    print(f"  valid_pillars: {valid_pillars}")
    print(f"  num_valid_pillars: {len(valid_pillars)}")
    
    if len(valid_pillars) >= 3:
        total_weight = sum(CSI_PILLAR_WEIGHTS[p] for p in valid_pillars.keys())
        print(f"  total_weight: {total_weight}")
        
        weighted_sum = sum(valid_pillars[p] * CSI_PILLAR_WEIGHTS[p] for p in valid_pillars)
        print(f"  weighted_sum: {weighted_sum}")
        
        csi_before_scaling = weighted_sum / total_weight
        print(f"  csi_before_scaling: {csi_before_scaling}")
        
        # The issue might be here - let's check the scaling
        csi_score = csi_before_scaling  # Remove the * 10 scaling
        print(f"  csi_score (without *10): {csi_score}")
        
        csi_score_with_scaling = csi_before_scaling * 10
        print(f"  csi_score (with *10): {csi_score_with_scaling}")
    
    print(f"\nFinal CSI Score: {analysis.csi_score}")
    
    # Let's also test the original calculation line by line from the service
    print(f"\n=== Testing Original Service Logic ===")
    
    # Reset analysis object
    analysis2 = DailyAnalysis(
        conversation_id=1,
        analysis_date=datetime.now().date(),
        sentiment_score=8.0,
        sentiment_shift=2.0,
        resolution_achieved=10.0,
        fcr_score=10.0,
        ces=7.0,
        first_response_time=60,
        avg_response_time=30,
        total_handling_time=5
    )
    
    # Step through the service logic line by line
    import numpy as np
    
    def safe_avg(values):
        valid_values = [v for v in values if v is not None]
        return np.mean(valid_values) if valid_values else None
    
    # Effectiveness
    analysis2.effectiveness_score = safe_avg([
        analysis2.resolution_achieved,
        analysis2.fcr_score
    ])
    print(f"effectiveness_score: {analysis2.effectiveness_score}")
    
    # Effort
    if analysis2.ces is not None:
        analysis2.effort_score = ((analysis2.ces - 1) / 6) * 10
    print(f"effort_score: {analysis2.effort_score}")
    
    # Efficiency - same complex logic
    def scale_time_service(value, max_time):
        if value is None or value < 0:
            return None
        capped_value = min(value, max_time * 3.0)
        normalized = capped_value / max_time
        efficiency_score = max(0, (1 - normalized)) * 10
        return min(10.0, max(0.0, efficiency_score))
    
    efficiency_scores = [
        scale_time_service(analysis2.first_response_time, 3600),
        scale_time_service(analysis2.avg_response_time, 1800), 
        scale_time_service(analysis2.total_handling_time * 60 if analysis2.total_handling_time is not None else None, 7200)
    ]
    analysis2.efficiency_score = safe_avg(efficiency_scores)
    print(f"efficiency_score: {analysis2.efficiency_score}")
    
    # Empathy
    analysis2.empathy_score = safe_avg([
        analysis2.sentiment_score,
        (analysis2.sentiment_shift + 5) if analysis2.sentiment_shift is not None else None
    ])
    print(f"empathy_score: {analysis2.empathy_score}")
    
    # Final CSI
    pillar_scores = {
        'effectiveness': analysis2.effectiveness_score,
        'effort': analysis2.effort_score,
        'efficiency': analysis2.efficiency_score,
        'empathy': analysis2.empathy_score
    }
    
    valid_pillars = {k: v for k, v in pillar_scores.items() if v is not None}
    print(f"valid_pillars: {valid_pillars}")
    
    if len(valid_pillars) < 3:
        print("Less than 3 pillars - CSI set to None")
        analysis2.csi_score = None
        return
    
    total_weight = sum(CSI_PILLAR_WEIGHTS[p] for p in valid_pillars.keys())
    print(f"total_weight: {total_weight}")
    
    if total_weight == 0:
        print("Total weight is 0 - CSI set to None")
        analysis2.csi_score = None
        return
    
    # This is the exact line from the service
    csi_score = sum(valid_pillars[p] * CSI_PILLAR_WEIGHTS[p] for p in valid_pillars) / total_weight * 10
    print(f"csi_score (service logic): {csi_score}")
    
    analysis2.csi_score = round(min(10.0, max(0.0, csi_score)), 2)
    print(f"final csi_score: {analysis2.csi_score}")

if __name__ == "__main__":
    debug_csi_calculation()