import praw
import sqlite3
import re
import requests
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_price(text):
    # Look for price patterns in common formats:
    # $6,250 or $3899 or $1,775
    price_patterns = [
        r'\$(\d{1,3}(?:,\d{3})*)',  # Matches $6,250
        r'\$(\d+)',                  # Matches $3899
        r'(?:price|asking|offered at).?\$(\d{1,3}(?:,\d{3})*)',  # Matches "Price: $6,250" or "Offered at $6,250"
        r'(?:price|asking|offered at).?\$(\d+)'                   # Matches "Price: $3899"
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(',', '')
            return int(price_str)
    return None

def extract_size(text):
    # Look for size patterns:
    # 36mm or 42MM or "Case diameter – 42MM" or "case measures about 39mm"
    size_patterns = [
        r'(?:case:.*?|case diameter.?)(\d{2})(?:\s*)?mm',  # Matches "Case: ... 36mm"
        r'(\d{2})(?:\s*)?mm(?:\s*)?(?:case|diameter)',     # Matches "36mm case"
        r'case measures.*?(\d{2})(?:\s*)?mm',              # Matches "case measures about 39mm"
        r'\b(\d{2})(?:\s*)?mm\b'                          # Simple 36mm pattern
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

def extract_reference(text):
    # Look for reference patterns:
    # Ref. 16234 or SBGR029 or 210.30.42.20.03.001
    ref_patterns = [
        r'(?:ref(?:erence)?\.?\s*(?:no\.?)?\s*)([\w.-]+)',  # Matches "Ref. 16234"
        r'(?:reference|model)\s*(?:#|number|no\.?)?\s*:?\s*([\w.-]+)',  # Matches "Reference: 16234" or "Model #: 210.30..."
        r'\b(?:SBGR|SBGA|SBGH|SBGJ|SBGM|SBGN|SBGR|SBGT|SBGY)\d{3}\b'  # Specific Grand Seiko patterns
    ]
    
    for pattern in ref_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            ref = match.group(1)
            # Filter out common false positives
            if ref.lower() not in ['wts', 'wtt', 'sale', 'sold']:
                return ref
    return None

def extract_year(text):
    # Look for year patterns:
    # 1993 or 2022 (in reasonable range)
    year_patterns = [
        r'\b((?:19[5-9]\d|20[0-2]\d))\b'  # Years from 1950-2029
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None

def extract_brand(text):
    # Common watch brands
    brands = {
        'rolex': 'Rolex',
        'omega': 'Omega',
        'grand seiko': 'Grand Seiko',
        'seiko': 'Seiko',
        'tudor': 'Tudor'
        # Add more brands as needed
    }
    
    text_lower = text.lower()
    for brand_lower, brand_proper in brands.items():
        if brand_lower in text_lower:
            return brand_proper
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
            full_text = f"{title}\n{submission.selftext}"
            
            # Only process [wts] posts
            if '[wts]' not in title.lower() and '[wts/wtt]' not in title.lower():
                continue

            # Extract information from both title and selftext
            price = extract_price(full_text)
            year = extract_year(full_text)
            ref_number = extract_reference(full_text)
            size = extract_size(full_text)
            brand = extract_brand(full_text)

            logger.info(f"Extracted data from {submission.title}:")
            logger.info(f"Price: {price}")
            logger.info(f"Year: {year}")
            logger.info(f"Reference: {ref_number}")
            logger.info(f"Size: {size}")

            try:
                cursor.execute('''
                    INSERT INTO watches 
                    (title, price, year, reference_number, size, brand, link)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (submission.title, price, year, ref_number, size, brand, submission.url))
                
                posts_added += 1
                logger.info(f"Added post {posts_added}/10: {submission.title}")
                
                # Send notification only for Rolex posts
                if 'rolex' in title.lower():
                    logger.info(f"Found Rolex post: {submission.title}")
                    send_notification(submission.title, price, submission.url, ONESIGNAL_API_URL, ONESIGNAL_APP_ID, ONESIGNAL_API_KEY)
                
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