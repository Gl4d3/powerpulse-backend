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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting PowerPulse Analytics Backend...")
    init_db()
    logger.info("Database initialized successfully")
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
