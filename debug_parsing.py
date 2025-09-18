"""
Debug the parsing step in detail
"""
import json
from services.file_service_optimized import OptimizedFileService

def debug_parsing():
    # Read the test file
    with open("test_conversation_proper_format.json", "r") as f:
        file_content = f.read()
    
    print("Raw file content:")
    print(file_content)
    print()
    
    # Parse manually to see structure
    parsed_data = json.loads(file_content)
    print(f"Parsed data type: {type(parsed_data)}")
    print(f"Keys: {list(parsed_data.keys())}")
    print(f"Is dict: {isinstance(parsed_data, dict)}")
    print(f"Number of keys: {len(parsed_data.keys())}")
    print(f"First key: {list(parsed_data.keys())[0]}")
    print()
    
    # Check the conditions in _parse_and_normalize_input
    if isinstance(parsed_data, dict):
        print("✓ Is dict")
        
        # Check for 'messages' key
        if 'messages' in parsed_data and isinstance(parsed_data['messages'], list):
            print("✓ Has 'messages' key with list value")
        else:
            print("✗ No 'messages' key or not a list")
        
        # Check if single-key object
        if len(parsed_data.keys()) == 1:
            print("✓ Single-key object")
            raw_messages = next(iter(parsed_data.values()))
            print(f"Value type: {type(raw_messages)}")
            print(f"Is list: {isinstance(raw_messages, list)}")
            if isinstance(raw_messages, list):
                print(f"✓ Single-key object with list value - should call _preprocess_and_group_raw_data")
            else:
                print("✗ Single-key object but value is not a list")
        else:
            print("✗ Not single-key object")
            print("→ Should call _normalize_grouped_data")
    
    # Test the actual parsing
    file_service = OptimizedFileService()
    try:
        grouped_data, customer_names = file_service._parse_and_normalize_input(file_content)
        print(f"\nActual parsing result:")
        print(f"Grouped data: {grouped_data}")
        print(f"Customer names: {customer_names}")
    except Exception as e:
        print(f"\nParsing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_parsing()