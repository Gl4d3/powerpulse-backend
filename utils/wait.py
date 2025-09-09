import time
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if len(sys.argv) > 1:
    try:
        seconds = int(sys.argv[1])
        logging.info(f"Waiting for {seconds} seconds...")
        time.sleep(seconds)
        logging.info("Wait complete.")
    except ValueError:
        logging.error("Invalid number of seconds provided.")
else:
    logging.warning("No wait time provided to wait.py.")
