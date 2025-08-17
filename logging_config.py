import logging
import sys
from pathlib import Path

def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler for all logs
            logging.FileHandler(log_dir / "powerpulse.log"),
            # File handler for errors only
            logging.FileHandler(log_dir / "errors.log", level=logging.ERROR)
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")
    
    return logger
