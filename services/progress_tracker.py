# import logging
# from typing import Dict, Optional, Any
# from datetime import datetime
# from sqlalchemy.orm import Session

# from models import ProgressUpdate

# logger = logging.getLogger(__name__)

# class ProgressTracker:
#     def start_upload(self, db: Session, upload_id: str, filename: str) -> None:
#         """Create a new progress tracking record in the database."""
#         existing_record = db.query(ProgressUpdate).filter_by(upload_id=upload_id).first()
#         if existing_record:
#             logger.warning(f"Progress record for upload_id {upload_id} already exists. Overwriting.")
#             db.delete(existing_record)
#             db.commit()

#         new_record = ProgressUpdate(
#             upload_id=upload_id,
#             filename=filename,
#             status='processing',
#             current_stage='initializing',
#             start_time=datetime.utcnow(),
#             last_update=datetime.utcnow()
#         )
#         db.add(new_record)
#         db.commit()
#         logger.info(f"Started tracking upload {upload_id} for file {filename}")

#     def update_progress(
#         self, 
#         db: Session,
#         upload_id: str, 
#         processed: int, 
#         total: int,
#         stage: str
#     ) -> None:
#         """Update progress for an upload."""
#         record = self.get_progress(db, upload_id)
#         if not record:
#             return

#         record.processed_conversations = processed
#         record.total_conversations = total
#         record.current_stage = stage
#         if total > 0:
#             record.progress_percentage = (processed / total) * 100
#         record.last_update = datetime.utcnow()
#         db.commit()
#         logger.info(f"Upload {upload_id}: {record.progress_percentage:.1f}% - {stage}")

#     def add_error(self, db: Session, upload_id: str, error: str) -> None:
#         """Add an error to the upload tracking."""
#         record = self.get_progress(db, upload_id)
#         if not record:
#             return
        
#         record.last_error = error
#         db.commit()

#     def complete_upload(self, db: Session, upload_id: str, success: bool = True) -> None:
#         """Mark upload as completed."""
#         record = self.get_progress(db, upload_id)
#         if not record:
#             return

#         record.status = 'completed' if success else 'failed'
#         record.progress_percentage = 100.0
#         record.end_time = datetime.utcnow()
#         record.last_update = record.end_time
#         db.commit()
        
#         duration = (record.end_time - record.start_time).total_seconds()
#         logger.info(f"Upload {upload_id} {'completed' if success else 'failed'} in {duration:.1f}s")

#     def get_progress(self, db: Session, upload_id: str) -> Optional[ProgressUpdate]:
#         """Get current progress for an upload."""
#         return db.query(ProgressUpdate).filter_by(upload_id=upload_id).first()

#     def get_all_active(self, db: Session) -> list[ProgressUpdate]:
#         """Get all active uploads."""
#         return db.query(ProgressUpdate).filter_by(status='processing').all()

# # Global progress tracker instance
# progress_tracker = ProgressTracker()