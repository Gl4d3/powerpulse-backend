import json
import random
import logging
from collections import defaultdict
from datetime import datetime

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INPUT_FILE_PATH = 'attached_assets/FB17-23.json'
OUTPUT_FILE_PATH = 'attached_assets/curated_sample.json'
SAMPLES_PER_DAY = 10
MIN_MESSAGES = 2
MAX_MESSAGES = 99

def main():
    """
    Creates a smaller, curated sample from a large JSON data file.
    """
    logging.info(f"Starting data sampling from {INPUT_FILE_PATH}...")

    try:
        with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Error reading or parsing source JSON file: {e}")
        return

    # The JSON file has the SQL query as the main key. The value is the list of messages.
    all_messages = next(iter(data.values()), [])
    if not all_messages:
        logging.warning("No messages found in the source JSON file.")
        return

    # Step 1: Group messages by conversation ID
    convs_by_id = defaultdict(list)
    for msg in all_messages:
        convs_by_id[msg.get('FB_ID')].append(msg)

    # Step 2: Filter conversations based on the number of 'to_company' messages
    logging.info(f"Filtering {len(convs_by_id)} total conversations...")
    filtered_conv_ids = set()
    for conv_id, messages in convs_by_id.items():
        to_company_count = sum(1 for msg in messages if msg.get('DIRECTION') == 'to_company')
        if MIN_MESSAGES <= to_company_count < MAX_MESSAGES:
            filtered_conv_ids.add(conv_id)
    logging.info(f"Found {len(filtered_conv_ids)} conversations matching the message count criteria ({MIN_MESSAGES}-{MAX_MESSAGES} to_company messages).")

    # Step 3: Group the filtered conversations by the dates they were active
    convs_by_date = defaultdict(list)
    for conv_id in filtered_conv_ids:
        messages = convs_by_id[conv_id]
        active_dates = set()
        for msg in messages:
            try:
                # Extract just the date part from the timestamp string
                ts_str = msg.get('SOCIAL_CREATE_TIME')
                if ts_str:
                    active_dates.add(datetime.fromisoformat(ts_str.replace('Z', '+00:00')).date())
            except (ValueError, TypeError):
                continue # Skip messages with invalid timestamps
        
        for active_date in active_dates:
            convs_by_date[active_date].append(conv_id)

    # Step 4: For each day, sample up to 10 conversations
    final_sampled_conv_ids = set()
    for day, conv_ids in convs_by_date.items():
        if len(conv_ids) > SAMPLES_PER_DAY:
            final_sampled_conv_ids.update(random.sample(conv_ids, SAMPLES_PER_DAY))
        else:
            final_sampled_conv_ids.update(conv_ids)
    
    logging.info(f"Final sample will contain {len(final_sampled_conv_ids)} unique conversations.")

    # Step 5: Create the final list of messages from the sampled conversations
    output_messages = [msg for msg in all_messages if msg.get('FB_ID') in final_sampled_conv_ids]

    # Step 6: Write the output file
    try:
        # The output should be a flat list of message objects, same as the input format
        output_data = {
            "description": f"Curated sample of {len(final_sampled_conv_ids)} conversations with {len(output_messages)} messages.",
            "messages": output_messages
        }
        with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        logging.info(f"Successfully created curated data sample at {OUTPUT_FILE_PATH}")
    except Exception as e:
        logging.error(f"Failed to write output file: {e}")

if __name__ == '__main__':
    main()
