from flask import Flask, render_template
from reddit_scraper import scrape_watchexchange, get_database_posts
import time
from datetime import datetime
import threading
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_scraper_periodically():
    while True:
        logger.info(f"Running scheduled scrape at {datetime.now()}")
        scrape_watchexchange()
        time.sleep(600)  # Sleep for 10 minutes

@app.route('/')
def home():
    posts = get_database_posts()
    last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template('index.html', posts=posts, last_update=last_update)

if __name__ == '__main__':
    # Start the periodic scraper in a background thread
    scraper_thread = threading.Thread(target=run_scraper_periodically, daemon=True)
    scraper_thread.start()
    
    app.run(debug=False, host='0.0.0.0')