import os
from typing import Dict, Any
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

    # Job and Batching Configuration (Legacy)
    MAX_TOKENS_PER_BATCH: int = 20000 # Max tokens to process in one batch
    BATCH_PROCESSING_DELAY_SECONDS: int = 10  # Delay between processing batches to manage rate limits
    AI_CONCURRENCY: int = 1  # Reduced from 5 to stay well below 15 RPM limit

    # Model configuration
    GPT_MODEL: str = "gpt-4o-mini"
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "")
    
    # ========== CONSTITUTIONAL COMPLIANCE SETTINGS ==========
    
    # AI Micro-Metrics Supremacy Requirements
    CONSTITUTIONAL_AI_SUPREMACY_ENABLED: bool = True
    REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE: float = 90.0  # Minimum AI insights coverage
    AI_METRICS_VALIDATION_INTERVAL_SECONDS: int = 300  # 5 minutes
    
    # Dual CSI Architecture Requirements
    CONSTITUTIONAL_DUAL_CSI_REQUIRED: bool = True
    CSI_CALCULATED_FIELD_REQUIRED: bool = True
    CSI_INFERRED_FIELD_REQUIRED: bool = True
    CSI_COMPLETENESS_THRESHOLD_PERCENTAGE: float = 95.0
    
    # Cost Reduction Constitutional Requirements (80% minimum)
    CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE: float = 80.0
    COST_OPTIMIZATION_TARGET_PERCENTAGE: float = 85.0  # Target above minimum
    COST_VALIDATION_ENABLED: bool = True
    
    # Processing Speed Constitutional Requirements (3-4 interactions/second)
    CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND: float = 3.0
    CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND: float = 4.0
    PROCESSING_SPEED_VALIDATION_ENABLED: bool = True
    
    # System Success Rate Constitutional Requirements
    CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE: float = 95.0
    SUCCESS_RATE_MONITORING_ENABLED: bool = True
    
    # ========== BATCH PROCESSING OPTIMIZATION SETTINGS ==========
    
    # Enhanced Batch Configuration
    BATCH_PROCESSING_ENABLED: bool = True
    ENHANCED_BATCH_SIZE_SMALL: int = 5  # For small files
    ENHANCED_BATCH_SIZE_MEDIUM: int = 10  # For medium files
    ENHANCED_BATCH_SIZE_LARGE: int = 15  # For large files
    MAX_CONCURRENT_BATCH_SESSIONS: int = 3
    
    # Batch Strategy Configuration
    BATCH_STRATEGY_AUTO_SELECTION: bool = True
    SMALL_FILE_THRESHOLD_INTERACTIONS: int = 50
    MEDIUM_FILE_THRESHOLD_INTERACTIONS: int = 200
    LARGE_FILE_THRESHOLD_INTERACTIONS: int = 500
    
    # Context Sharing and Optimization
    BATCH_CONTEXT_SHARING_ENABLED: bool = True
    PROMPT_COMPRESSION_ENABLED: bool = True
    BATCH_PROMPT_OPTIMIZATION_ENABLED: bool = True
    CONTEXT_WINDOW_SIZE_TOKENS: int = 30000  # Gemini Pro context window
    
    # ========== PERFORMANCE MONITORING SETTINGS ==========
    
    # Performance Tracking
    PERFORMANCE_MONITORING_ENABLED: bool = True
    PERFORMANCE_METRICS_COLLECTION_INTERVAL_SECONDS: int = 60
    REAL_TIME_METRICS_ENABLED: bool = True
    
    # Cost Tracking and Optimization
    COST_TRACKING_ENABLED: bool = True
    API_COST_CALCULATION_ENABLED: bool = True
    COST_OPTIMIZATION_REPORTING_ENABLED: bool = True
    
    # Processing Speed Monitoring
    PROCESSING_SPEED_MONITORING_ENABLED: bool = True
    THROUGHPUT_TARGET_INTERACTIONS_PER_HOUR: int = 12000  # 3.33 per second average
    LATENCY_TARGET_MILLISECONDS: int = 2000  # 2 second max per interaction
    
    # ========== SESSION MANAGEMENT SETTINGS ==========
    
    # Upload Session Configuration
    SESSION_TIMEOUT_SECONDS: int = 3600  # 1 hour
    SESSION_RETRY_MAX_ATTEMPTS: int = 3
    SESSION_RETRY_DELAY_SECONDS: int = 300  # 5 minutes
    
    # Session Status Tracking
    SESSION_STATUS_UPDATE_INTERVAL_SECONDS: int = 30
    SESSION_PROGRESS_REPORTING_ENABLED: bool = True
    SESSION_REAL_TIME_UPDATES_ENABLED: bool = True
    
    # ========== WORKER CONFIGURATION ==========
    
    # Enhanced Worker Settings
    WORKER_POLL_INTERVAL_SECONDS: int = 5
    WORKER_BATCH_CHECK_INTERVAL_SECONDS: int = 10
    WORKER_CONSTITUTIONAL_CHECK_INTERVAL_SECONDS: int = 300  # 5 minutes
    
    # Worker Concurrency and Performance
    WORKER_MAX_CONCURRENT_BATCHES: int = 3
    WORKER_BATCH_PROCESSING_ENABLED: bool = True
    WORKER_LEGACY_JOB_SUPPORT_ENABLED: bool = True
    
    # ========== GEMINI API OPTIMIZATION SETTINGS ==========
    
    # Gemini-Specific Batch Optimization
    GEMINI_BATCH_OPTIMIZATION_ENABLED: bool = True
    GEMINI_CONTEXT_CACHING_ENABLED: bool = True
    GEMINI_PROMPT_COMPRESSION_RATIO: float = 0.6  # Target 40% compression
    
    # Gemini Rate Limiting and Cost Control
    GEMINI_REQUESTS_PER_MINUTE: int = 15
    GEMINI_TOKENS_PER_MINUTE: int = 32000
    GEMINI_COST_PER_1K_TOKENS: float = 0.00025  # Gemini Pro pricing
    
    # Gemini Batch Processing Parameters
    GEMINI_MAX_BATCH_SIZE: int = 20
    GEMINI_OPTIMAL_BATCH_SIZE: int = 12
    GEMINI_BATCH_TIMEOUT_SECONDS: int = 120
    
    # ========== DATA INTEGRITY AND VALIDATION SETTINGS ==========
    
    # Data Integrity Constitutional Requirements
    DATA_INTEGRITY_VALIDATION_ENABLED: bool = True
    ORPHANED_RECORDS_CHECK_ENABLED: bool = True
    REFERENTIAL_INTEGRITY_ENFORCEMENT: bool = True
    
    # Validation and Quality Assurance
    INPUT_VALIDATION_STRICT_MODE: bool = True
    OUTPUT_VALIDATION_ENABLED: bool = True
    SCHEMA_VALIDATION_ENABLED: bool = True
    
    # ========== LOGGING AND MONITORING CONFIGURATION ==========
    
    # Enhanced Logging
    LOG_LEVEL: str = "INFO"
    CONSTITUTIONAL_COMPLIANCE_LOGGING: bool = True
    PERFORMANCE_METRICS_LOGGING: bool = True
    BATCH_PROCESSING_DETAILED_LOGGING: bool = True
    
    # Monitoring and Alerting
    CONSTITUTIONAL_VIOLATIONS_ALERTING: bool = True
    PERFORMANCE_DEGRADATION_ALERTING: bool = True
    COST_THRESHOLD_ALERTING: bool = True
    
    # ========== FEATURE FLAGS ==========
    
    # Enhanced Features
    ENHANCED_UPLOAD_ENDPOINTS_ENABLED: bool = True
    BATCH_CONFIG_ENDPOINTS_ENABLED: bool = True
    CONSTITUTIONAL_ENDPOINTS_ENABLED: bool = True
    SESSION_STATUS_ENDPOINTS_ENABLED: bool = True
    
    # Backward Compatibility
    LEGACY_UPLOAD_ENDPOINTS_ENABLED: bool = True
    LEGACY_JOB_PROCESSING_ENABLED: bool = True

    # Qdrant configuration (optional)
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    
    # Server configuration (for Docker/Cloud Run compatibility)
    PORT: int = 8000
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"  # Ignore extra environment variables
    }

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
        
        # Constitutional Compliance Validation
        self._validate_constitutional_settings()
        
        # Performance Settings Validation
        self._validate_performance_settings()
        
        # Batch Processing Validation
        self._validate_batch_settings()
    
    def _validate_constitutional_settings(self):
        """Validate constitutional compliance settings."""
        if self.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE < 0 or self.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE > 100:
            raise ValueError("CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE must be between 0 and 100")
        
        if self.COST_OPTIMIZATION_TARGET_PERCENTAGE < self.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE:
            raise ValueError("COST_OPTIMIZATION_TARGET_PERCENTAGE must be >= CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE")
        
        if self.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND <= 0:
            raise ValueError("CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND must be positive")
        
        if self.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND <= self.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND:
            raise ValueError("CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND must be > CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND")
        
        if self.CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE < 0 or self.CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE > 100:
            raise ValueError("CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE must be between 0 and 100")
        
        if self.REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE < 0 or self.REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE > 100:
            raise ValueError("REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE must be between 0 and 100")
    
    def _validate_performance_settings(self):
        """Validate performance and monitoring settings."""
        if self.SESSION_TIMEOUT_SECONDS <= 0:
            raise ValueError("SESSION_TIMEOUT_SECONDS must be positive")
        
        if self.SESSION_RETRY_MAX_ATTEMPTS < 0:
            raise ValueError("SESSION_RETRY_MAX_ATTEMPTS must be non-negative")
        
        if self.WORKER_MAX_CONCURRENT_BATCHES <= 0:
            raise ValueError("WORKER_MAX_CONCURRENT_BATCHES must be positive")
        
        if self.THROUGHPUT_TARGET_INTERACTIONS_PER_HOUR <= 0:
            raise ValueError("THROUGHPUT_TARGET_INTERACTIONS_PER_HOUR must be positive")
    
    def _validate_batch_settings(self):
        """Validate batch processing settings."""
        if self.ENHANCED_BATCH_SIZE_SMALL <= 0:
            raise ValueError("ENHANCED_BATCH_SIZE_SMALL must be positive")
        
        if self.ENHANCED_BATCH_SIZE_MEDIUM < self.ENHANCED_BATCH_SIZE_SMALL:
            raise ValueError("ENHANCED_BATCH_SIZE_MEDIUM must be >= ENHANCED_BATCH_SIZE_SMALL")
        
        if self.ENHANCED_BATCH_SIZE_LARGE < self.ENHANCED_BATCH_SIZE_MEDIUM:
            raise ValueError("ENHANCED_BATCH_SIZE_LARGE must be >= ENHANCED_BATCH_SIZE_MEDIUM")
        
        if self.SMALL_FILE_THRESHOLD_INTERACTIONS <= 0:
            raise ValueError("SMALL_FILE_THRESHOLD_INTERACTIONS must be positive")
        
        if self.MEDIUM_FILE_THRESHOLD_INTERACTIONS <= self.SMALL_FILE_THRESHOLD_INTERACTIONS:
            raise ValueError("MEDIUM_FILE_THRESHOLD_INTERACTIONS must be > SMALL_FILE_THRESHOLD_INTERACTIONS")
        
        if self.LARGE_FILE_THRESHOLD_INTERACTIONS <= self.MEDIUM_FILE_THRESHOLD_INTERACTIONS:
            raise ValueError("LARGE_FILE_THRESHOLD_INTERACTIONS must be > MEDIUM_FILE_THRESHOLD_INTERACTIONS")
    
    def get_batch_size_for_file_size(self, interaction_count: int) -> int:
        """Determine optimal batch size based on file size (interaction count)."""
        if interaction_count <= self.SMALL_FILE_THRESHOLD_INTERACTIONS:
            return self.ENHANCED_BATCH_SIZE_SMALL
        elif interaction_count <= self.MEDIUM_FILE_THRESHOLD_INTERACTIONS:
            return self.ENHANCED_BATCH_SIZE_MEDIUM
        else:
            return self.ENHANCED_BATCH_SIZE_LARGE
    
    def get_constitutional_compliance_config(self) -> Dict[str, Any]:
        """Get constitutional compliance configuration as a dictionary."""
        return {
            "ai_supremacy_enabled": self.CONSTITUTIONAL_AI_SUPREMACY_ENABLED,
            "dual_csi_required": self.CONSTITUTIONAL_DUAL_CSI_REQUIRED,
            "min_cost_reduction_percentage": self.CONSTITUTIONAL_MIN_COST_REDUCTION_PERCENTAGE,
            "min_interactions_per_second": self.CONSTITUTIONAL_MIN_INTERACTIONS_PER_SECOND,
            "max_interactions_per_second": self.CONSTITUTIONAL_MAX_INTERACTIONS_PER_SECOND,
            "min_success_rate_percentage": self.CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE,
            "ai_insights_coverage_percentage": self.REQUIRED_AI_INSIGHTS_COVERAGE_PERCENTAGE,
        }
    
    def get_performance_targets(self) -> Dict[str, Any]:
        """Get performance targets as a dictionary."""
        return {
            "cost_reduction_target": self.COST_OPTIMIZATION_TARGET_PERCENTAGE,
            "throughput_target_per_hour": self.THROUGHPUT_TARGET_INTERACTIONS_PER_HOUR,
            "latency_target_ms": self.LATENCY_TARGET_MILLISECONDS,
            "success_rate_target": self.CONSTITUTIONAL_MIN_SUCCESS_RATE_PERCENTAGE,
            "batch_timeout_seconds": self.GEMINI_BATCH_TIMEOUT_SECONDS,
        }
    
    def get_batch_processing_config(self) -> Dict[str, Any]:
        """Get batch processing configuration as a dictionary."""
        return {
            "enabled": self.BATCH_PROCESSING_ENABLED,
            "max_concurrent_sessions": self.MAX_CONCURRENT_BATCH_SESSIONS,
            "batch_sizes": {
                "small": self.ENHANCED_BATCH_SIZE_SMALL,
                "medium": self.ENHANCED_BATCH_SIZE_MEDIUM,
                "large": self.ENHANCED_BATCH_SIZE_LARGE,
            },
            "thresholds": {
                "small_file": self.SMALL_FILE_THRESHOLD_INTERACTIONS,
                "medium_file": self.MEDIUM_FILE_THRESHOLD_INTERACTIONS,
                "large_file": self.LARGE_FILE_THRESHOLD_INTERACTIONS,
            },
            "optimization": {
                "context_sharing": self.BATCH_CONTEXT_SHARING_ENABLED,
                "prompt_compression": self.PROMPT_COMPRESSION_ENABLED,
                "gemini_optimization": self.GEMINI_BATCH_OPTIMIZATION_ENABLED,
            },
        }

settings = Settings()