"""Debug the large sample validation errors."""

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

# Get a single conversation for debugging
conn = sqlite3.connect('powerpulse.db')
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
LIMIT 1
"""

df = pd.read_sql_query(query, conn)
conn.close()

print("Sample conversation data:")
print(df.iloc[0].to_dict())

# Test generating metrics for this conversation
conv = df.iloc[0].to_dict()
print(f"\nTesting metric generation for conversation {conv['conversation_id']}...")

try:
    # Base metrics on conversation characteristics
    np.random.seed(conv['conversation_id'])
    message_count = conv['message_count']
    duration_mins = conv.get('duration_minutes', 0) or 0
    agent_ratio = conv.get('agent_response_ratio', 0.5) or 0.5
    
    print(f"Message count: {message_count}")
    print(f"Duration minutes: {duration_mins}")
    print(f"Agent ratio: {agent_ratio}")
    
    # Generate metrics with realistic correlation
    complexity_factor = min(1.0, (message_count - 2) / 10 + duration_mins / 60)
    print(f"Complexity factor: {complexity_factor}")
    
    # Generate realistic metrics
    base_resolution = max(2.0, 10.0 - complexity_factor * 6)
    resolution_achieved = max(0, min(10, np.random.normal(base_resolution, 2)))
    fcr_score = resolution_achieved * np.random.uniform(0.8, 1.2)
    
    print(f"Resolution achieved: {resolution_achieved}")
    print(f"FCR score: {fcr_score}")
    
    # Test creating DailyAnalysis - check all required fields
    from sqlalchemy.inspection import inspect
    
    # Get column names from the model
    mapper = inspect(DailyAnalysis)
    column_names = [column.key for column in mapper.columns]
    print(f"DailyAnalysis columns: {column_names}")
    
    # Create metrics with all necessary fields
    metrics = {
        'sentiment_score': 5.0,
        'sentiment_shift': 1.0,
        'resolution_achieved': resolution_achieved,
        'fcr_score': fcr_score,
        'ces': 3.5,
        'first_response_time': 300.0,
        'avg_response_time': 180.0,
        'total_handling_time': 15.0
    }
    
    print(f"\nTest metrics: {metrics}")
    
    analysis = DailyAnalysis(
        conversation_id=conv['conversation_id'],
        analysis_date=datetime.now().date(),
        **metrics
    )
    
    print(f"DailyAnalysis created successfully")
    print(f"Analysis attributes: {[attr for attr in dir(analysis) if not attr.startswith('_')]}")
    
    # Test CSI calculation
    service = EnhancedAnalyticsService()
    service.calculate_and_set_csi_score(analysis)
    
    print(f"CSI Score: {analysis.csi_score}")
    print(f"Effectiveness: {analysis.effectiveness_score}")
    print(f"Effort: {analysis.effort_score}")
    print(f"Efficiency: {analysis.efficiency_score}")
    print(f"Empathy: {analysis.empathy_score}")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()