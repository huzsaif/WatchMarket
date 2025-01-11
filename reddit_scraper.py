import praw
import sqlite3
import re
import requests
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_watchexchange():
    logger.info("Starting scrape_watchexchange function")
    
    # Debug: Print current directory and files
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Files in directory: {os.listdir()}")
    
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

    # Debug: Print Reddit connection status
    logger.info("Reddit connection established")
    
    # Connect to database
    db_path = 'watches.db'
    logger.info(f"Attempting to connect to database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Debug: Print database status before clearing
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='watches'")
        table_exists = cursor.fetchone()[0]
        logger.info(f"Watches table exists: {bool(table_exists)}")
        
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM watches")
            count_before = cursor.fetchone()[0]
            logger.info(f"Posts in database before clearing: {count_before}")

        # Clear existing entries
        cursor.execute("DROP TABLE IF EXISTS watches")
        cursor.execute('''
            CREATE TABLE watches
            (title TEXT, price INTEGER, year INTEGER, 
             reference_number TEXT, size INTEGER, brand TEXT,
             link TEXT UNIQUE)
        ''')
        conn.commit()
        logger.info("Database table recreated")

        # Get latest posts
        logger.info("Fetching new posts from r/watchexchange")
        subreddit = reddit.subreddit("watchexchange")
        posts_added = 0
        
        for submission in subreddit.new(limit=30):  # Higher limit to ensure we get 10 [WTS] posts
            if posts_added >= 10:  # Stop after 10 posts
                break
                
            title = submission.title.lower()
            logger.info(f"Processing post: {submission.title}")
            
            # Only process [wts] posts
            if '[wts]' not in title and '[wts/wtt]' not in title:
                logger.info("Skipping - not a [WTS] post")
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

            # Check if it's a Rolex post (for notifications only)
            is_rolex = 'rolex' in title
            brand = 'Rolex' if is_rolex else None

            try:
                cursor.execute('''
                    INSERT INTO watches 
                    (title, price, year, reference_number, size, brand, link)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (submission.title, price, year, ref_number, size, brand, submission.url))
                
                posts_added += 1
                logger.info(f"Added post {posts_added}/10: {submission.title}")
                
                # Send notification only for Rolex posts
                if is_rolex:
                    logger.info(f"Found Rolex post: {submission.title}")
                    send_notification(submission.title, price, submission.url, ONESIGNAL_API_URL, ONESIGNAL_APP_ID, ONESIGNAL_API_KEY)
                
            except sqlite3.IntegrityError as e:
                logger.error(f"Database error: {e}")
                continue

        conn.commit()
        
        # Debug: Print final database status
        cursor.execute("SELECT COUNT(*) FROM watches")
        final_count = cursor.fetchone()[0]
        logger.info(f"Final number of posts in database: {final_count}")
        
        # Debug: Print all posts in database
        cursor.execute("SELECT title FROM watches")
        all_posts = cursor.fetchall()
        logger.info("Posts in database:")
        for post in all_posts:
            logger.info(f"- {post[0]}")

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