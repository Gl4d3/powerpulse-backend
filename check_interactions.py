#!/usr/bin/env python3

from database import SessionLocal
from models import InteractionAnalysis

def check_populated_interactions():
    """Check what interactions have been populated with CSI data"""
    db = SessionLocal()
    try:
        # Get interactions with CSI scores
        interactions = db.query(InteractionAnalysis).filter(
            InteractionAnalysis.csi_score.isnot(None)
        ).limit(3).all()
        
        if interactions:
            for ia in interactions:
                print(f"ID: {ia.id}")
                print(f"  CSI Score: {ia.csi_score}")
                print(f"  Sentiment: {ia.sentiment_score}")
                print(f"  Resolution: {ia.resolution_achieved}")
                print(f"  FCR: {ia.fcr_score}")
                print(f"  CES: {ia.ces}")
                print(f"  Effectiveness: {ia.effectiveness_score}")
                print(f"  Effort: {ia.effort_score}")
                print("---")
        else:
            print("No interactions with CSI scores found")
            # Check if we have any interactions at all
            total = db.query(InteractionAnalysis).count()
            print(f"Total interactions in DB: {total}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_populated_interactions()