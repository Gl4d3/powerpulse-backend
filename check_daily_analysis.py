"""
Check DailyAnalysis results
"""
from database import get_db
from models import DailyAnalysis

db = next(get_db())
analyses = db.query(DailyAnalysis).all()

print(f"Found {len(analyses)} DailyAnalysis records:")
for a in analyses:
    print(f"ID {a.id}:")
    print(f"  - sentiment_score: {a.sentiment_score}")
    print(f"  - resolution_achieved: {a.resolution_achieved}")
    print(f"  - fcr_score: {a.fcr_score}")
    print(f"  - ces: {a.ces}")
    print(f"  - has csi_score: {hasattr(a, 'csi_score')}")
    if hasattr(a, 'csi_score'):
        print(f"  - csi_score: {a.csi_score}")
    print()