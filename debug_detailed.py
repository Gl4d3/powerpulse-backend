"""
Enhanced debug script with step-by-step debugging
"""
import asyncio
import json
from database import get_db
from services.file_service_optimized import OptimizedFileService
from models import Conversation, Message
import uuid
from datetime import datetime

async def detailed_debug():
    db = next(get_db())
    
    # Read and parse the test file
    with open("test_conversation_proper_format.json", "r") as f:
        file_content = f.read()
    
    file_service = OptimizedFileService()
    
    # Step 1: Test parsing
    print("=== Step 1: Testing parsing ===")
    grouped_data, customer_names = file_service._parse_and_normalize_input(file_content)
    print(f"Grouped data keys: {list(grouped_data.keys())}")
    print(f"Customer names: {customer_names}")
    
    for chat_id, messages in grouped_data.items():
        print(f"Chat {chat_id}: {len(messages)} messages")
    
    # Step 2: Test validation
    print("\n=== Step 2: Testing message validation ===")
    for chat_id, messages in grouped_data.items():
        print(f"\nValidating messages for chat {chat_id}:")
        for i, msg in enumerate(messages):
            is_valid = file_service._validate_message(msg)
            print(f"  Message {i}: {is_valid}")
            if not is_valid:
                print(f"    Content: {msg}")
                # Check what fields are missing
                required_fields = ['MESSAGE_CONTENT', 'DIRECTION', 'SOCIAL_CREATE_TIME']
                missing = [field for field in required_fields if field not in msg]
                if missing:
                    print(f"    Missing fields: {missing}")
                if msg.get('DIRECTION') not in ['to_company', 'to_client']:
                    print(f"    Invalid direction: {msg.get('DIRECTION')}")
    
    # Step 3: Test cleaning
    print("\n=== Step 3: Testing message cleaning ===")
    for chat_id, messages in grouped_data.items():
        valid_messages = [file_service._clean_message(msg, chat_id) for msg in messages if file_service._validate_message(msg)]
        print(f"Chat {chat_id}: {len(valid_messages)} valid messages after cleaning")
        
        if valid_messages:
            print(f"  First cleaned message: {valid_messages[0]}")
    
    # Step 4: Test grouping by day
    print("\n=== Step 4: Testing day grouping ===")
    all_possible_analyses = {}
    for chat_id, messages in grouped_data.items():
        valid_messages = [file_service._clean_message(msg, chat_id) for msg in messages if file_service._validate_message(msg)]
        if not valid_messages:
            print(f"  No valid messages for {chat_id}")
            continue
        
        messages_by_day = file_service._group_messages_by_day(valid_messages)
        print(f"Chat {chat_id}: {len(messages_by_day)} days")
        
        for day, day_messages in messages_by_day.items():
            all_possible_analyses[(chat_id, day)] = day_messages
            print(f"  Day {day}: {len(day_messages)} messages")
    
    print(f"\nTotal possible analyses: {len(all_possible_analyses)}")

if __name__ == "__main__":
    asyncio.run(detailed_debug())