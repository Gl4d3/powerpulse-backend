"""
Debug script to test file processing directly
"""
import asyncio
import json
from database import get_db
from services.file_service_optimized import OptimizedFileService
from models import Conversation, Message
import uuid

async def test_file_processing():
    db = next(get_db())
    
    # Read the test file
    with open("test_conversation_proper_format.json", "r") as f:
        file_content = f.read()
    
    print("Test file content:")
    print(file_content[:500] + "...")
    
    # Parse it to verify structure
    parsed_data = json.loads(file_content)
    print(f"\nParsed structure keys: {list(parsed_data.keys())}")
    
    if "test_chat_001" in parsed_data:
        messages = parsed_data["test_chat_001"]
        print(f"Found {len(messages)} messages")
        
        # Check the first message structure
        first_msg = messages[0]
        print(f"First message keys: {list(first_msg.keys())}")
        print(f"First message: {first_msg}")
    
    # Test the file processing
    print("\n=== Testing File Processing ===")
    file_service = OptimizedFileService()
    
    upload_id = str(uuid.uuid4())
    
    try:
        conversations_processed, messages_processed, result_id = await file_service.process_grouped_chats_json(
            file_content=file_content,
            db=db,
            upload_id=upload_id,
            force_reprocess=True
        )
        
        print(f"Processing result:")
        print(f"- Conversations processed: {conversations_processed}")
        print(f"- Messages processed: {messages_processed}")
        print(f"- Result ID: {result_id}")
        
        # Check what was actually created in the database
        conversations = db.query(Conversation).all()
        print(f"\nDatabase check:")
        print(f"- Total conversations in DB: {len(conversations)}")
        
        for conv in conversations:
            messages = db.query(Message).filter(Message.conversation_id == conv.id).all()
            print(f"- Conversation {conv.fb_chat_id}: {len(messages)} messages")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_file_processing())