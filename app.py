from flask import Flask, jsonify
from reddit_scraper import scrape_watchexchange
import time
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

last_scrape_time = None
SCRAPE_INTERVAL = 600  # 10 minutes in seconds

@app.route('/')
def home():
    global last_scrape_time
    current_time = time.time()
    
    # Run scraper if it's the first time or if 10 minutes have passed
    if last_scrape_time is None or (current_time - last_scrape_time) >= SCRAPE_INTERVAL:
        logger.info(f"Running scraper at {datetime.now()}")
        scrape_watchexchange()
        last_scrape_time = current_time
    
    return jsonify({"status": "alive"})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')