import sqlite3
import logging
from datetime import datetime

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    db_path = 'powerpulse.db'
    target_daily_analysis_id = 127  # From the user's log

    logging.info(f"Starting diagnostic for daily_analysis_id: {target_daily_analysis_id}")

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Get the DailyAnalysis record
        cursor.execute("SELECT conversation_id, analysis_date FROM daily_analyses WHERE id = ?", (target_daily_analysis_id,))
        analysis_record = cursor.fetchone()

        if not analysis_record:
            logging.error(f"Could not find DailyAnalysis record with id: {target_daily_analysis_id}")
            return

        conversation_id, analysis_date = analysis_record
        logging.info(f"Found DailyAnalysis record: [ID: {target_daily_analysis_id}, ConversationID: {conversation_id}, AnalysisDate: {analysis_date}]")

        # 2. Get all messages for the parent conversation
        cursor.execute("SELECT social_create_time, message_content FROM messages WHERE conversation_id = ? ORDER BY social_create_time", (conversation_id,))
        messages = cursor.fetchall()

        if not messages:
            logging.warning(f"Found NO messages in the database for ConversationID: {conversation_id}")
        else:
            logging.info(f"Found {len(messages)} total messages for ConversationID: {conversation_id}. Their timestamps are:")
            for row in messages:
                print(f"  - {row[0]}")
        
        # 3. Compare and conclude
        logging.info("--- DIAGNOSIS ---")
        logging.info(f"The 'orphaned' DailyAnalysis record has a date of: {analysis_date}")
        
        date_found = False
        for row in messages:
            msg_date_str = row[0].split(' ')[0] # Get just the YYYY-MM-DD part
            if msg_date_str == analysis_date:
                date_found = True
                break
        
        if not date_found:
            logging.error(f"CONFIRMED: None of the actual message timestamps for this conversation match the analysis_date of the orphaned record.")
            logging.error("This proves the ingestion logic error where messages are discarded if a daily analysis record already exists.")
        else:
            logging.warning("UNEXPECTED: A message with a matching date was found. The issue may be more complex.")

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()
