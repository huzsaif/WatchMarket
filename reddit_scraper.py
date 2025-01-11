import praw
import sqlite3
import re
import requests
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_watchexchange():
    logger.info("Starting scrape_watchexchange function")
    
    # Initialize Reddit instance with your credentials
    reddit = praw.Reddit(
        client_id="796nqtKpzmGTsgPaL8v9eA",
        client_secret="JqQTxcEkhFduFzwmXG-ND2cV9UXeWw",
        user_agent="WatchTool/0.1 by zayfuh"
    )

    # OneSignal API credentials
    ONESIGNAL_API_URL = "https://onesignal.com/api/v1/notifications"
    ONESIGNAL_APP_ID = "3a92834d-ceb3-400c-8c68-73d52157b773"
    ONESIGNAL_API_KEY = "os_v2_app_hkjigtoownaazddiopkscv5xonygya235bcur753ksbmknxrf5sixmu2cswdke5oildjettbfscfvny2qw4c66ewviyrmz3jm5bcc4a"

    # Connect to database
    conn = sqlite3.connect('watches.db')
    cursor = conn.cursor()

    try:
        # Clear existing entries
        logger.info("Clearing existing database entries")
        cursor.execute("DELETE FROM watches")
        conn.commit()

        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watches
            (title TEXT, price INTEGER, year INTEGER, 
             reference_number TEXT, size INTEGER, brand TEXT,
             link TEXT UNIQUE)
        ''')
        conn.commit()

        # Get latest posts
        logger.info("Fetching new posts from r/watchexchange")
        subreddit = reddit.subreddit("watchexchange")
        for submission in subreddit.new(limit=100):  # Increased limit to get more posts
            title = submission.title.lower()
            
            # Only process [wts] posts
            if '[wts]' not in title and '[wts/wtt]' not in title:
                continue

            # Extract information
            price_match = re.search(r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', submission.title)
            price = int(price_match.group(1).replace(',', '')) if price_match else None
            
            year_match = re.search(r'\b(19|20)\d{2}\b', submission.title)
            year = int(year_match.group()) if year_match else None
            
            ref_match = re.search(r'\b[a-zA-Z0-9]{3,8}(?:-[a-zA-Z0-9]+)?\b', submission.title)
            ref_number = ref_match.group() if ref_match else None
            
            size_match = re.search(r'\b(\d{2})mm\b', submission.title)
            size = int(size_match.group(1)) if size_match else None

            # Check if it's a Rolex post
            is_rolex = 'rolex' in title
            brand = 'Rolex' if is_rolex else None

            if is_rolex:
                logger.info(f"Found Rolex post: {submission.title}")
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO watches 
                        (title, price, year, reference_number, size, brand, link)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (submission.title, price, year, ref_number, size, brand, submission.url))
                    
                    # Send notification for new Rolex posts
                    send_notification(submission.title, price, submission.url, ONESIGNAL_API_URL, ONESIGNAL_APP_ID, ONESIGNAL_API_KEY)
                    
                except sqlite3.IntegrityError as e:
                    logger.error(f"Database error: {e}")
                    continue

        conn.commit()
        logger.info("Database updated successfully")

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

def send_notification(title, price, link, api_url, app_id, api_key):
    headers = {
        "accept": "application/json",
        "Authorization": f"Basic {api_key}",
        "content-type": "application/json"
    }
    
    price_text = f"${price:,}" if price else "Price unknown"
    
    payload = {
        "app_id": app_id,
        "included_segments": ["Subscribed Users"],
        "contents": {"en": f"New Rolex Listed: {title}\nPrice: {price_text}"},
        "url": link
    }
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload
        )
        logger.info(f"Notification sent with status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending notification: {e}")

if __name__ == "__main__":
    scrape_watchexchange()