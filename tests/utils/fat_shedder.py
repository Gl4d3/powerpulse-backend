import json
from datetime import datetime

def preprocess_conversations_for_llm(input_filepath: str, output_filepath: str):
    """
    Reads a raw JSON file of conversations, groups messages by chat ID,
    cleans and formats them into a simple transcript, and saves the
    processed data to a new JSON file.

    Args:
        input_filepath (str): Path to the raw JSON conversation data.
        output_filepath (str): Path where the processed JSON will be saved.
    """
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file {input_filepath} was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_filepath}.")
        return

    processed_conversations = {}

    # The top-level keys in your JSON are the chat_ids
    for chat_id, messages in raw_data.items():
        
        # Temporary list to hold message data for sorting
        message_tuples = []

        for message in messages:
            content = message.get('MESSAGE_CONTENT')
            
            # Skip messages with no text content
            if not content or not content.strip():
                continue

            direction = message.get('DIRECTION')
            timestamp_str = message.get('SOCIAL_CREATE_TIME')
            
            # Use a tuple to store data for reliable sorting by timestamp
            try:
                # Parse the timestamp string to a datetime object for accurate sorting
                timestamp_obj = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                message_tuples.append((timestamp_obj, direction, content))
            except (ValueError, TypeError):
                # Skip if timestamp is invalid or missing
                continue

        # Sort messages chronologically
        message_tuples.sort(key=lambda x: x[0])

        # Format the sorted messages into a clean transcript
        transcript_lines = []
        for timestamp_obj, direction, content in message_tuples:
            speaker = "Customer" if direction == 'to_company' else "Agent"
            timestamp_formatted = timestamp_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
            transcript_lines.append(f"[{timestamp_formatted}] {speaker}: {content}")
        
        # Join the lines into a single string for the LLM
        if transcript_lines:
            processed_conversations[chat_id] = "\n".join(transcript_lines)

    # Save the processed data to the output file
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(processed_conversations, f, indent=2)

    print(f"Processing complete. Cleaned data saved to {output_filepath}")
    print(f"Processed {len(processed_conversations)} conversations.")

# --- How to use the script ---
# 1. Save your raw data to a file named 'raw_conversations.json'
# 2. Run this script.
if __name__ == '__main__':
    # Replace with the actual path to your large JSON file
    # input_file = 'attached_assets/snippet_1755240593792.json' 
    input_file = 'attached_assets/grouped_chats_1755190636068.json' 
    output_file = 'attached_assets/processed_transcripts_for_llm.json'
    
    preprocess_conversations_for_llm(input_file, output_file)
