#!/usr/bin/env python3

import asyncio
from database import SessionLocal
from services.interaction_analytics_service import InteractionAnalyticsService
from services.gemini_service import GeminiService
from models import InteractionAnalysis
import config

async def test_interaction_batch():
    """Test the fixed interaction analytics service"""
    db = SessionLocal()
    try:
        settings = config.Settings()
        gemini = GeminiService(settings.GEMINI_API_KEY)
        service = InteractionAnalyticsService(gemini)
        
        # Get one interaction to test
        interactions = db.query(InteractionAnalysis).limit(1).all()
        if interactions:
            print(f"Testing with interaction ID: {interactions[0].id}")
            result = await service.analyze_interactions_batch(db, interactions)
            print(f"Success! Result keys: {list(result.keys())}")
            if result:
                first_result = next(iter(result.values()))
                print(f"First result CSI: {first_result.overall_csi}")
                print(f"Effectiveness: {first_result.effectiveness_score}")
                print(f"Effort: {first_result.effort_score}")
        else:
            print("No interactions found in database")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_interaction_batch())