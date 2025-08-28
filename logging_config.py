import logging
import sys
from pathlib import Path

def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Define a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Console Handler ---
    # Shows our "catchy" INFO logs and any warnings/errors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # --- Application Trace Handler (with UTF-8 encoding) ---
    # Logs only our INFO-level application trace to a clean file
    app_trace_handler = logging.FileHandler(log_dir / "app_trace.log", mode='w', encoding='utf-8')
    app_trace_handler.setLevel(logging.INFO)
    app_trace_handler.setFormatter(formatter)
    # A filter to only allow logs from our specific application modules
    class AppLogFilter(logging.Filter):
        def filter(self, record):
            return record.name.startswith('services') or record.name.startswith('main')
    app_trace_handler.addFilter(AppLogFilter())

    # --- Root Logger Configuration ---
    # Configure the root logger to capture everything at INFO level
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [console_handler, app_trace_handler]

    # --- Quieting Down Noisy Loggers ---
    # Set specific noisy loggers to a higher level to quiet them down
    logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)
    logging.getLogger("uvicorn.access").setLevel(logging.ERROR) # Silence Uvicorn access logs
    
    logging.info("Logging configured successfully. Application trace will be in logs/app_trace.log")
