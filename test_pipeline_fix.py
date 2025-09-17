#!/usr/bin/env python3

import asyncio
from utils.test_curated_sample_pipeline import CuratedSampleTester

async def test_upload():
    """Test just the upload part to see if the JSON serialization fix works"""
    tester = CuratedSampleTester()
    try:
        upload_result = await tester._upload_curated_sample()
        print(f'Upload successful! Conversations: {upload_result["conversations_created"]}')
        
        # Test pipeline with just 1 conversation
        conversation_ids = [upload_result["conversation_ids"][0]] if upload_result["conversation_ids"] else []
        if conversation_ids:
            print(f"Testing pipeline with conversation ID: {conversation_ids[0]}")
            pipeline_result = await tester._run_interaction_pipeline(conversation_ids)
            print(f"Pipeline result keys: {list(pipeline_result.keys())}")
            print(f"Processing summary: {pipeline_result['processing_summary']}")
        
    except Exception as e:
        print(f'Test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_upload())