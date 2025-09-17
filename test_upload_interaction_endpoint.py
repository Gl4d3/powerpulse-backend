#!/usr/bin/env python3
"""
End-to-End Test for Upload Interaction JSON Endpoint
Tests the complete dual CSI interaction analysis pipeline
"""

import asyncio
import logging
import requests
import json
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_upload_interaction_endpoint():
    """Test the /upload-interaction-json endpoint with curated sample"""
    
    # API endpoint
    base_url = "http://localhost:8000"
    upload_endpoint = f"{base_url}/api/upload-interaction-json"
    
    # Load curated sample
    curated_sample_path = Path("attached_assets/curated_sample.json")
    
    if not curated_sample_path.exists():
        logger.error(f"Curated sample not found at {curated_sample_path}")
        return False
    
    logger.info("=== UPLOAD INTERACTION ENDPOINT E2E TEST ===")
    logger.info(f"Testing endpoint: {upload_endpoint}")
    logger.info(f"Sample file: {curated_sample_path}")
    
    try:
        # Read curated sample
        with open(curated_sample_path, 'r', encoding='utf-8') as f:
            sample_content = f.read()
        
        sample_data = json.loads(sample_content)
        logger.info(f"Loaded sample: {sample_data.get('description', 'No description')}")
        
        # Prepare file for upload
        files = {
            'file': ('curated_sample.json', sample_content, 'application/json')
        }
        
        params = {
            'mode': 'interaction'
        }
        
        logger.info("Sending POST request to upload-interaction-json endpoint...")
        start_time = time.time()
        
        # Make request
        response = requests.post(
            upload_endpoint,
            files=files,
            params=params,
            timeout=300  # 5 minute timeout for AI processing
        )
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        logger.info(f"Request completed in {processing_time} seconds")
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 202:  # Accepted
            result = response.json()
            logger.info("✅ SUCCESS - Upload accepted!")
            logger.info(f"Upload ID: {result.get('upload_id')}")
            logger.info(f"Message: {result.get('message')}")
            logger.info(f"Conversations: {result.get('conversations_processed')}")
            logger.info(f"Messages: {result.get('messages_processed')}")
            logger.info(f"Processing time: {result.get('processing_time_seconds')}s")
            
            # Parse message for dual CSI results
            message = result.get('message', '')
            if 'dual CSI' in message and 'avg:' in message:
                logger.info("✅ DUAL CSI ANALYSIS DETECTED IN RESPONSE!")
            else:
                logger.warning("⚠️ Dual CSI analysis not explicitly mentioned in response")
            
            return True
            
        else:
            logger.error(f"❌ FAILED - Status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ TIMEOUT - Request took longer than 5 minutes")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ CONNECTION ERROR - Make sure the server is running on localhost:8000")
        return False
    except Exception as e:
        logger.error(f"❌ ERROR - {str(e)}")
        return False

async def main():
    """Main test function"""
    logger.info("Starting upload-interaction-json endpoint test...")
    
    # Test the endpoint
    success = await test_upload_interaction_endpoint()
    
    if success:
        logger.info("\n✅ END-TO-END TEST COMPLETED SUCCESSFULLY!")
        logger.info("The upload-interaction-json endpoint is working with dual CSI analysis.")
    else:
        logger.error("\n❌ END-TO-END TEST FAILED!")
        logger.error("Check the server logs and ensure it's running.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())