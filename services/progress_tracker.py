import logging
from typing import Dict, Optional
from datetime import datetime
import asyncio
import json

logger = logging.getLogger(__name__)

class ProgressTracker:
    def __init__(self):
        self.active_uploads = {}
        self.upload_lock = asyncio.Lock()
    
    async def start_upload(self, upload_id: str, total_conversations: int) -> None:
        """Start tracking a new upload"""
        async with self.upload_lock:
            self.active_uploads[upload_id] = {
                'total_conversations': total_conversations,
                'processed_conversations': 0,
                'current_stage': 'initializing',
                'progress_percentage': 0.0,
                'start_time': datetime.utcnow(),
                'last_update': datetime.utcnow(),
                'status': 'processing',
                'errors': [],
                'filtered_autoresponses': 0,
                'gpt_calls_made': 0
            }
            logger.info(f"Started tracking upload {upload_id} with {total_conversations} conversations")
    
    async def update_progress(
        self, 
        upload_id: str, 
        processed: int, 
        stage: str, 
        details: Optional[str] = None
    ) -> None:
        """Update progress for an upload"""
        async with self.upload_lock:
            if upload_id not in self.active_uploads:
                return
            
            progress = self.active_uploads[upload_id]
            progress['processed_conversations'] = processed
            progress['current_stage'] = stage
            progress['progress_percentage'] = (processed / progress['total_conversations']) * 100
            progress['last_update'] = datetime.utcnow()
            
            if details:
                progress['details'] = details
            
            logger.info(f"Upload {upload_id}: {progress['progress_percentage']:.1f}% - {stage}")
    
    async def increment_gpt_calls(self, upload_id: str) -> None:
        """Increment GPT API call counter"""
        async with self.upload_lock:
            if upload_id in self.active_uploads:
                self.active_uploads[upload_id]['gpt_calls_made'] += 1
    
    async def increment_filtered(self, upload_id: str) -> None:
        """Increment filtered autoresponse counter"""
        async with self.upload_lock:
            if upload_id in self.active_uploads:
                self.active_uploads[upload_id]['filtered_autoresponses'] += 1
    
    async def add_error(self, upload_id: str, error: str) -> None:
        """Add an error to the upload tracking"""
        async with self.upload_lock:
            if upload_id in self.active_uploads:
                self.active_uploads[upload_id]['errors'].append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': error
                })
    
    async def complete_upload(self, upload_id: str, success: bool = True) -> None:
        """Mark upload as completed"""
        async with self.upload_lock:
            if upload_id not in self.active_uploads:
                return
            
            progress = self.active_uploads[upload_id]
            progress['status'] = 'completed' if success else 'failed'
            progress['progress_percentage'] = 100.0 if success else progress['progress_percentage']
            progress['end_time'] = datetime.utcnow()
            progress['duration_seconds'] = (progress['end_time'] - progress['start_time']).total_seconds()
            
            logger.info(f"Upload {upload_id} {'completed' if success else 'failed'} in {progress['duration_seconds']:.1f}s")
    
    def get_progress(self, upload_id: str) -> Optional[Dict]:
        """Get current progress for an upload"""
        return self.active_uploads.get(upload_id)
    
    def get_all_active(self) -> Dict:
        """Get all active uploads"""
        return {
            upload_id: progress 
            for upload_id, progress in self.active_uploads.items()
            if progress['status'] == 'processing'
        }
    
    async def cleanup_old_uploads(self, max_age_hours: int = 24) -> None:
        """Clean up old upload tracking data"""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        async with self.upload_lock:
            to_remove = []
            for upload_id, progress in self.active_uploads.items():
                if progress['start_time'].timestamp() < cutoff_time:
                    to_remove.append(upload_id)
            
            for upload_id in to_remove:
                del self.active_uploads[upload_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old upload records")

# Global progress tracker instance
progress_tracker = ProgressTracker()