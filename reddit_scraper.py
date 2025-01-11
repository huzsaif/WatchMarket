import praw
import sqlite3
import re
import requests
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_price(title):
    # Look for price patterns like $1,234 or $1234 or $1,234.56
    price_match = re.search(r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+)', title)
    if price_match:
        # Remove commas and convert to integer
        price_str = price_match.group(1).replace(',', '')
        # Remove decimal points if they exist
        price_str = price_str.split('.')[0]
        return int(price_str)
    return None

def extract_reference(title):
    # Common Rolex reference patterns
    ref_patterns = [
        r'(?:ref|reference|ref\.|reference\.)?\s*(?:no|\#|number)?\.?\s*([\d]{4,6})',  # Basic number
        r'(?:ref|reference|ref\.|reference\.)?\s*(?:no|\#|number)?\.?\s*([\d\w]{3,8}(?:-[\d\w]+)?)',  # Alphanumeric
        r'\b([0-9]{3,6}(?:-[0-9A-Z]+)?)\b'  # Numbers with possible suffix
    ]
    
    for pattern in ref_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            ref = match.group(1)
            # Exclude common false positives
            if ref.lower() not in ['wts', 'sale', 'sold']:
                return ref
    return None

def extract_size(title):
    # Look for patterns like 41mm or 41 mm
    size_match = re.search(r'(\d{2})(?:\s*)?mm', title, re.IGNORECASE)
    if size_match:
        return int(size_match.group(1))
    return None

def extract_year(title):
    # Look for 4-digit years between 1950 and current year
    year_match = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', title)
    if year_match:
        year = int(year_match.group(1))
        current_year = datetime.now().year
        if 1950 <= year <= current_year:
            return year
    return None

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
        posts_added = 0
        
        for submission in subreddit.new(limit=30):  # Higher limit to ensure we get 10 [WTS] posts
            if posts_added >= 10:  # Stop after 10 posts
                break
                
            title = submission.title
            title_lower = title.lower()
            
            # Only process [wts] posts
            if '[wts]' not in title_lower and '[wts/wtt]' not in title_lower:
                continue

            # Extract information using improved functions
            price = extract_price(title)
            year = extract_year(title)
            ref_number = extract_reference(title)
            size = extract_size(title)

            # Check if it's a Rolex post
            is_rolex = 'rolex' in title_lower
            brand = 'Rolex' if is_rolex else None

            try:
                cursor.execute('''
                    INSERT INTO watches 
                    (title, price, year, reference_number, size, brand, link)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (title, price, year, ref_number, size, brand, submission.url))
                
                posts_added += 1
                logger.info(f"Added post {posts_added}/10: {title}")
                logger.info(f"Extracted data: Price={price}, Year={year}, Ref={ref_number}, Size={size}")
                
                # Send notification only for Rolex posts
                if is_rolex:
                    logger.info(f"Found Rolex post: {title}")
                    send_notification(title, price, submission.url, ONESIGNAL_API_URL, ONESIGNAL_APP_ID, ONESIGNAL_API_KEY)
                
            except sqlite3.IntegrityError as e:
                logger.error(f"Database error: {e}")
                continue

        conn.commit()
        logger.info(f"Database updated successfully with {posts_added} posts")

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