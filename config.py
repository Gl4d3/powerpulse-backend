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
    
    # Original Key => akioko367@gmail.com
    # OPENAI_API_KEY: str = "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"
    
    # The way of the Dao Key => agarcia1234.com@gmail.com
    OPENAI_API_KEY: str = "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"
    
    # GEMINI_API_KEY: str = "AIzaSyDM9GssixzNISUbofkVLttZBco1BvyI2eE" 
    # GEMINI_API_KEY: str = "AIzaSyC89aAsZ_37Q8UBY9UMlrLOCzQtwgvtWjg"
    GEMINI_API_KEY: str = "AIzaSyB0TNJzIJAc4hAJiw5CYdhrxDuQz-1sha8"
    AI_SERVICE: str = "gemini"  # NEW: Choose between "openai" or "gemini"

    # Job and Batching Configuration
    MAX_TOKENS_PER_JOB: int = 16000
    AI_CONCURRENCY: int = 5
    
    # Model configuration
    GPT_MODEL: str = "gpt-4o-mini"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
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