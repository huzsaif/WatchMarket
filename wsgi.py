import os
import threading
import logging
from app import app
import reddit_scraper
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_scraper():
    while True:
        try:
            logger.info("Starting scraper...")
            reddit_scraper.scrape_watchexchange()
            logger.info("Scraper finished. Sleeping for 10 minutes...")
            time.sleep(600)  # Sleep for 10 minutes
        except Exception as e:
            logger.error(f"Error in scraper: {e}")
            logger.info("Retrying in 60 seconds...")
            time.sleep(60)

# Start scraper thread when wsgi loads
logger.info("Starting background scraper thread...")
scraper_thread = threading.Thread(target=run_scraper, daemon=True)
scraper_thread.start() 