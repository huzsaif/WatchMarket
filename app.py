import os
from flask import Flask, render_template, send_from_directory
import sqlite3
from reddit_scraper import scrape_watchexchange
import logging
import schedule
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/OneSignalSDKWorker.js')
def serve_onesignal_worker():
    return send_from_directory('static', 'OneSignalSDKWorker.js')

@app.route('/OneSignalSDK.sw.js')
def serve_onesignal_sdk():
    return send_from_directory('static', 'OneSignalSDKWorker.js')

@app.route("/")
def home():
    try:
        # Run scraper to get latest posts
        logger.info("Running scraper for fresh data...")
        scrape_watchexchange()
        logger.info("Scraper finished, fetching data...")

        # Get the latest posts
        conn = sqlite3.connect("watches.db")
        cursor = conn.cursor()
        cursor.execute('''
            SELECT title, price, year, reference_number, size, brand, link 
            FROM watches 
            ORDER BY ROWID DESC 
            LIMIT 10
        ''')
        watches = cursor.fetchall()
        return render_template("index.html", watches=watches)
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error accessing data: {str(e)}"
    finally:
        if 'conn' in locals():
            conn.close()

def schedule_scraper():
    # Schedule the scraper to run every 10 minutes instead of every second
    schedule.every(10).minutes.do(run_scraper)
    
    while True:
        schedule.run_pending()
        time.sleep(1)  # Sleep for 1 second between schedule checks

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)