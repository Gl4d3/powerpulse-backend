"""
This script exports the contents of the main database tables to CSV files
for easy visualization and debugging.
"""
import pandas as pd
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from database import engine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def export_tables_to_csv():
    """
    Connects to the database and exports specified tables to CSV files
    in a dedicated, timestamped folder.
    """
    tables_to_export = [
        "conversations",
        "daily_analyses",
        "messages",
        "jobs",
        "metrics",
        "processed_chats",
    ]

    try:
        # Create a dedicated directory for exports
        export_dir = project_root / "db_export"
        export_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        with engine.connect() as connection:
            logging.info("Successfully connected to the database.")
            for table_name in tables_to_export:
                logging.info(f"Exporting table: {table_name}...")
                try:
                    df = pd.read_sql_table(table_name, connection)
                    output_filename = export_dir / f"{timestamp}_{table_name}.csv"
                    df.to_csv(output_filename, index=False)
                    logging.info(f"Successfully exported {table_name} to {output_filename}")
                except Exception as e:
                    logging.error(f"Could not export table {table_name}. It might be empty or not exist. Error: {e}")
            logging.info("Database export process complete.")

    except Exception as e:
        logging.error(f"Failed to connect to the database. Error: {e}")

if __name__ == "__main__":
    export_tables_to_csv()
