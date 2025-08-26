# reset_database.py
"""
This script resets the application's database. It connects to the database
specified in the configuration, drops all existing tables, and then recreates
them based on the current SQLAlchemy models.

This is a destructive operation and should be used with caution. It is primarily
intended for development and testing environments to ensure a clean, up-to-date
database schema.
"""

import logging
from database import engine, Base
from models import Conversation, Message, ProcessedChat, Metric, Job

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def reset_database():
    """
    Drops all tables from the database and recreates them based on the
    current models.
    """
    try:
        logging.info("Starting database reset...")

        # The Base.metadata object contains all the schema information
        # of the declarative models.
        
        logging.info("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        logging.info("All tables dropped successfully.")

        logging.info("Creating new tables based on current models...")
        Base.metadata.create_all(bind=engine)
        logging.info("All tables created successfully.")

        logging.info("Database has been reset.")

    except Exception as e:
        logging.error(f"An error occurred during the database reset: {e}")
        # It might be useful to see the full traceback for debugging
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # This confirmation step prevents accidental execution.
    confirm = input("Are you sure you want to completely reset the database? "
                    "All data will be lost. (yes/no): ")
    if confirm.lower() == 'yes':
        reset_database()
    else:
        logging.info("Database reset cancelled.")
