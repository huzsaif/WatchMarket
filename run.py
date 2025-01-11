import os
import threading
from app import app
import reddit_scraper
import time

def run_scraper():
    while True:
        try:
            reddit_scraper.scrape_watchexchange()
            print("Sleeping for 10 minutes...")
            time.sleep(600)  # Sleep for 10 minutes
        except Exception as e:
            print(f"Error occurred: {e}")
            print("Retrying in 60 seconds...")
            time.sleep(60)

# Start scraper in a background thread when gunicorn loads the app
scraper_thread = threading.Thread(target=run_scraper, daemon=True)
scraper_thread.start() 