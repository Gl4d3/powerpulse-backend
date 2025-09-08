"""
API Key validation endpoints for testing OpenAI and Gemini API keys
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from typing import Optional

# Import the AI services
from services.gemini_service import GeminiService
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class APIKeyTestResponse(BaseModel):
    """Response model for API key test"""
    service: str
    api_key_valid: bool
    message: str
    model_used: Optional[str] = None
    test_response: Optional[str] = None
    error_details: Optional[str] = None

@router.get("/test-api-key", response_model=APIKeyTestResponse)
async def test_configured_api_key():
    """
    Test the currently configured AI service API key.
    Returns validation status and a simple test response.
    """
    service = settings.AI_SERVICE.lower()
    
    try:
        if service == "gemini":
            return await _test_gemini_api_key()
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown AI service configured: {service}"
            )
    except Exception as e:
        logger.error(f"API key test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"API key test failed: {str(e)}"
        )

@router.get("/test-gemini", response_model=APIKeyTestResponse)
async def test_gemini_api_key():
    """
    Test the Gemini API key specifically.
    """
    if not settings.GEMINI_API_KEY:
        return APIKeyTestResponse(
            service="gemini",
            api_key_valid=False,
            message="Gemini API key not configured",
            error_details="GEMINI_API_KEY environment variable is not set"
        )
    
    return await _test_gemini_api_key()

async def _test_gemini_api_key() -> APIKeyTestResponse:
    """
    Internal function to test Gemini API key
    """
    try:
        gemini_service = GeminiService(settings.GEMINI_API_KEY)
        
        # Make a simple test call
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        response = model.generate_content("Hello! Please respond with 'API key is working' to confirm the connection.")
        
        test_response = response.text if hasattr(response, 'text') else str(response)
        
        return APIKeyTestResponse(
            service="gemini",
            api_key_valid=True,
            message="Gemini API key is valid and working",
            model_used=settings.GEMINI_MODEL,
            test_response=test_response[:200]  # Truncate for safety
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Gemini API key test failed: {error_msg}")
        
        # Check for common error patterns
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            message = "Gemini API key is invalid"
        elif "quota" in error_msg.lower() or "exhaust" in error_msg.lower():
            message = "Gemini API quota exceeded"
        elif "permission" in error_msg.lower():
            message = "Gemini API permission denied"
        else:
            message = "Gemini API key test failed"
            
        return APIKeyTestResponse(
            service="gemini",
            api_key_valid=False,
            message=message,
            model_used=settings.GEMINI_MODEL,
            error_details=error_msg
        )

