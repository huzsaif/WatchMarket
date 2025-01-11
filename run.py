import os
import threading
import time
import logging
from app import app
from reddit_scraper import scrape_watchexchange

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_scraper_periodically():
    while True:
        try:
            logger.info("Starting scheduled scrape...")
            scrape_watchexchange()
            logger.info("Scrape completed, sleeping for 60 seconds...")
            time.sleep(60)  # Run every minute for testing
        except Exception as e:
            logger.error(f"Error in scraper: {e}")
            time.sleep(10)  # Wait before retrying

if __name__ == "__main__":
    # Start scraper in background thread
    scraper_thread = threading.Thread(target=run_scraper_periodically, daemon=True)
    scraper_thread.start()
    logger.info("Scraper thread started")

    # Start Flask app
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port) 