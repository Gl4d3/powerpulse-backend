from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import os

from config import settings

logger = logging.getLogger(__name__)

# Create SQLite engine with better connection handling
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # 30 second timeout
        "isolation_level": None  # Auto-commit mode
    },
    echo=True,  # Enable SQL query logging
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600  # Recycle connections every hour
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Prevent expired object issues
)

Base = declarative_base()

def get_db():
    """Dependency to get database session with better error handling"""
    db = SessionLocal()
    try:
        # Test connection
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        db.rollback()
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error(f"Error closing database session: {e}")

def init_db():
    """Initialize database tables with better error handling"""
    try:
        from models import Message, Conversation, ProcessedChat, Metric
        
        # Check if database file exists and is writable
        db_path = settings.DATABASE_URL.replace('sqlite:///', '')
        if os.path.exists(db_path):
            logger.info(f"Database file exists: {db_path}")
            # Test if file is writable
            try:
                with open(db_path, 'a') as f:
                    pass
                logger.info("Database file is writable")
            except PermissionError:
                logger.error(f"Database file is not writable: {db_path}")
                raise
        
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
        
        # Test database operations
        with SessionLocal() as test_db:
            test_db.execute(text("SELECT COUNT(*) FROM conversations"))
            logger.info("Database operations test successful")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def check_database_health():
    """Check if database is accessible and working"""
    try:
        with SessionLocal() as db:
            # Test basic operations
            result = db.execute(text("SELECT COUNT(*) FROM conversations")).scalar()
            logger.info(f"Database health check passed. Conversations count: {result}")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
