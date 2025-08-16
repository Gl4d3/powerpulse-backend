import os
from typing import Optional

class Settings:
    # Database
    DATABASE_URL: str = "sqlite:///./powerpulse.db"
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", default="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")
    OPENAI_MODEL: str = "gpt-4o-mini"  # Using GPT-4o-mini as specified
    
    # File upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "uploads"
    
    # Cache
    CACHE_PROCESSED_CHATS: bool = True
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Background tasks
    BACKGROUND_TASK_TIMEOUT: int = 3600  # 1 hour
    
    def __init__(self):
        # Ensure upload directory exists
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")

settings = Settings()
