import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database configuration
    DATABASE_URL: str = "sqlite:///./powerpulse.db"
    
    # File upload configuration
    MAX_FILE_SIZE: int = 52428800  # 50MB in bytes
    UPLOAD_DIR: str = "uploads"
    
    # Cache configuration
    CACHE_PROCESSED_CHATS: bool = True
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Background tasks
    BACKGROUND_TASK_TIMEOUT: int = 3600  # 1 hour
    
    # AI Service Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")  # Loaded from .env file
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")  # Loaded from .env file
    AI_SERVICE: str = "gemini"  # Choose between "openai" or "gemini"

    # Job and Batching Configuration
    MAX_TOKENS_PER_BATCH: int = 8000  # Reduced significantly to ensure output fits within 8K tokens
    BATCH_PROCESSING_DELAY_SECONDS: int = 5
    AI_CONCURRENCY: int = 1  # Reduced from 5 to stay well below 15 RPM limit

    # Model configuration
    GPT_MODEL: str = "gpt-4o-mini"
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    
    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure upload directory exists
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        
        # Validate that at least one AI service is configured
        if not self.OPENAI_API_KEY and not self.GEMINI_API_KEY:
            raise ValueError("Either OPENAI_API_KEY or GEMINI_API_KEY environment variable is required")
        
        # Validate AI service selection
        if self.AI_SERVICE.lower() not in ["openai", "gemini"]:
            raise ValueError("AI_SERVICE must be either 'openai' or 'gemini'")
        
        # Validate service-specific API key
        if self.AI_SERVICE.lower() == "openai" and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when AI_SERVICE is 'openai'")
        if self.AI_SERVICE.lower() == "gemini" and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required when AI_SERVICE is 'gemini'")

settings = Settings()