from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from contextlib import asynccontextmanager

from database import init_db
from routes.upload import router as upload_router
from routes.metrics import router as metrics_router  
from routes.conversations import router as conversations_router
from routes.export import router as export_router
from routes.progress import router as progress_router
from database import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_health():
    """Check if database is accessible and working"""
    try:
        with SessionLocal() as db:
            # Test basic operations
            result = db.execute("SELECT COUNT(*) FROM conversations").scalar()
            logger.info(f"Database health check passed. Conversations count: {result}")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting PowerPulse Analytics Backend...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized successfully")
    
    # Health check
    if not check_database_health():
        logger.error("Database health check failed!")
        raise RuntimeError("Database is not accessible")
    
    logger.info("Database health check passed")
    yield
    
    # Shutdown
    logger.info("Shutting down PowerPulse Analytics Backend...")

app = FastAPI(
    title="PowerPulse Analytics",
    description="Customer satisfaction analytics backend for Facebook chat data",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(metrics_router, prefix="/api", tags=["metrics"])
app.include_router(conversations_router, prefix="/api", tags=["conversations"])
app.include_router(export_router, prefix="/api", tags=["export"])
app.include_router(progress_router, prefix="/api", tags=["progress"])

@app.get("/")
async def root():
    return {
        "message": "PowerPulse Analytics API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "PowerPulse Analytics"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
