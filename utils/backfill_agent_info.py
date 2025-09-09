import json
import sqlite3
from datetime import datetime
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_timestamp(ts_str):
    """Parses the specific ISO 8601 format from the JSON file to a naive datetime object."""
    if not ts_str or not isinstance(ts_str, str):
        return None
    try:
        # Handles ISO format like "2025-08-18T10:55:25.000Z"
        aware_dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return aware_dt.replace(tzinfo=None)
    except ValueError:
        logging.warning(f"Could not parse timestamp: {ts_str}")
        return None

def get_conversation_pk(cursor, fb_chat_id):
    """Fetches the primary key of a conversation from its fb_chat_id."""
    cursor.execute("SELECT id FROM conversations WHERE fb_chat_id = ?", (fb_chat_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def main():
    json_path = 'attached_assets/FB17-23.json'
    db_path = 'powerpulse.db'
    
    logging.info(f"Starting agent_info backfill from {json_path} into {db_path}...")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Error reading or parsing JSON file: {e}")
        return

    # The JSON file has the SQL query as the main key. The value is the list of messages.
    messages = next(iter(data.values()), [])
    if not messages:
        logging.warning("No messages found in the JSON file.")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        updated_count = 0
        not_found_count = 0
        
        convo_pk_cache = {}

        for msg in messages:
            direction = msg.get('DIRECTION')
            agent_username = msg.get('AGENT_USERNAME')
            
            if direction == 'to_client' and agent_username:
                fb_id = msg.get('FB_ID')
                social_create_time_str = msg.get('SOCIAL_CREATE_TIME')
                agent_email = msg.get('AGENT_EMAIL')

                if not fb_id or not social_create_time_str:
                    continue

                social_create_time = parse_timestamp(social_create_time_str)
                if not social_create_time:
                    continue
                
                if fb_id not in convo_pk_cache:
                    convo_pk_cache[fb_id] = get_conversation_pk(cursor, fb_id)
                
                convo_pk = convo_pk_cache[fb_id]
                if not convo_pk:
                    continue

                agent_info = json.dumps({
                    "name": agent_username,
                    "email": agent_email
                })

                # SQLAlchemy stores datetimes with 6 microsecond precision.
                # Python's fromisoformat can produce more, so we format it to match.
                ts_for_match = social_create_time.strftime('%Y-%m-%d %H:%M:%S.%f')

                cursor.execute(
                    """
                    UPDATE messages
                    SET agent_info = ?
                    WHERE conversation_id = ? AND social_create_time = ?
                    """,
                    (agent_info, convo_pk, ts_for_match)
                )
                
                if cursor.rowcount > 0:
                    updated_count += 1
                else:
                    not_found_count += 1

        conn.commit()
        logging.info("Backfill complete.")
        logging.info(f"Successfully updated {updated_count} messages.")
        if not_found_count > 0:
            logging.warning(f"Could not find a matching DB record for {not_found_count} messages from the JSON file.")

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()
