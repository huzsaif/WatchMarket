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

if __name__ == "__main__":
    # Start scraper in a background thread
    scraper_thread = threading.Thread(target=run_scraper, daemon=True)
    scraper_thread.start()
    
    # Start the Flask app
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port) 