"""Test small sample first."""

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
        
        # Generate metrics with realistic correlation
        complexity_factor = min(1.0, (message_count - 2) / 10 + duration_mins / 60)
        
        # Effectiveness metrics (0-10 scale)
        base_resolution = max(2.0, 10.0 - complexity_factor * 6)
        resolution_achieved = max(0, min(10, np.random.normal(base_resolution, 2)))
        fcr_score = resolution_achieved * np.random.uniform(0.8, 1.2)
        
        # Effort (CES scale 1-7, then converted to 0-10)
        base_ces = min(7.0, 2.0 + complexity_factor * 4)
        ces = max(1, min(7, np.random.normal(base_ces, 1)))
        
        # Efficiency (time-based)
        first_response_time = conv.get('first_response_time_calc')
        if first_response_time is None or first_response_time < 0:
            first_response_time = np.random.lognormal(np.log(300), 1.5)
        
        avg_response_time = first_response_time * np.random.uniform(0.3, 0.8)
        total_handling_time = max(1, duration_mins + np.random.normal(0, 10))
        
        # Empathy metrics
        base_sentiment = 3 + (resolution_achieved / 10) * 4
        sentiment_score = max(0, min(10, np.random.normal(base_sentiment, 1.5)))
        
        if resolution_achieved > 7:
            sentiment_shift = np.random.uniform(0.5, 3.0)
        elif resolution_achieved < 4:
            sentiment_shift = np.random.uniform(-3.0, -0.5)
        else:
            sentiment_shift = np.random.uniform(-1.0, 1.0)
        
        return {
            'conversation_id': conv['conversation_id'],
            'sentiment_score': round(sentiment_score, 2),
            'sentiment_shift': round(sentiment_shift, 2),
            'resolution_achieved': round(resolution_achieved, 2),
            'fcr_score': round(fcr_score, 2),
            'ces': round(ces, 2),
            'first_response_time': round(first_response_time, 2),
            'avg_response_time': round(avg_response_time, 2),
            'total_handling_time': round(total_handling_time, 2)
        }

validator = RealDataCSIValidator()

# Test with just 3 conversations
conversations = validator.get_conversation_sample(3)
print(f"Retrieved {len(conversations)} conversations")

for i, conv in enumerate(conversations):
    print(f"\nTesting conversation {i+1}: {conv['conversation_id']}")
    try:
        metrics = validator.generate_realistic_metrics(conv)
        print(f"  Generated metrics: {metrics}")
        
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
        
        validator.service.calculate_and_set_csi_score(analysis)
        
        print(f"  CSI: {analysis.csi_score}")
        print(f"  Pillars: E={analysis.effectiveness_score:.2f}, Ef={analysis.effort_score:.2f}, Ec={analysis.efficiency_score:.2f}, Em={analysis.empathy_score:.2f}")
        print(f"  ✅ SUCCESS")
        
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

print("\nSmall sample test complete!")