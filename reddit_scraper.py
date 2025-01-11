import praw
import sqlite3
import re
import requests
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_data(text):
    # Price: Look for $ followed by numbers
    price_match = re.search(r'\$(\d+(?:,\d{3})*)', text)
    price = int(price_match.group(1).replace(',', '')) if price_match else None

    # Year: Look for 4-digit year
    year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', text)
    year = int(year_match.group(1)) if year_match else None

    # Reference: Look for "Ref." or "Reference" followed by numbers/letters
    ref_match = re.search(r'(?:Ref(?:erence)?\.?\s*(?:no\.?)?\s*)([A-Za-z0-9.-]+)', text)
    if not ref_match:
        # Try finding standalone reference patterns
        ref_match = re.search(r'\b([A-Z0-9]{4,}(?:-[A-Z0-9]+)*)\b', text)
    ref_number = ref_match.group(1) if ref_match else None

    # Size: Look for XX mm or XXmm
    size_match = re.search(r'(\d{2})\s*mm', text)
    size = int(size_match.group(1)) if size_match else None

    # Brand detection
    brand = None
    text_lower = text.lower()
    if 'rolex' in text_lower:
        brand = 'Rolex'
    elif 'omega' in text_lower:
        brand = 'Omega'
    elif 'grand seiko' in text_lower:
        brand = 'Grand Seiko'
    elif 'seiko' in text_lower:
        brand = 'Seiko'
    elif 'tudor' in text_lower:
        brand = 'Tudor'
    elif 'casio' in text_lower:
        brand = 'Casio'

    return price, year, ref_number, size, brand

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
        
        for submission in subreddit.new(limit=30):
            if posts_added >= 10:
                break
                
            title = submission.title
            post_author = submission.author
            
            # Only process [wts] posts
            if '[wts]' not in title.lower() and '[wts/wtt]' not in title.lower():
                continue

            # Extract data from title first
            title_price, title_year, title_ref, title_size, title_brand = extract_data(title)
            logger.info(f"From title - Price: {title_price}, Year: {title_year}, Ref: {title_ref}, Size: {title_size}, Brand: {title_brand}")

            # Get the author's comment
            submission.comments.replace_more(limit=None)
            author_comment = None
            for comment in submission.comments.list():
                if comment.author == post_author:
                    author_comment = comment.body
                    logger.info("Found author's comment")
                    break

            # Extract data from author's comment if found
            if author_comment:
                comment_price, comment_year, comment_ref, comment_size, comment_brand = extract_data(author_comment)
                logger.info(f"From author comment - Price: {comment_price}, Year: {comment_year}, Ref: {comment_ref}, Size: {comment_size}, Brand: {comment_brand}")
            else:
                logger.info("No author comment found")
                comment_price = comment_year = comment_ref = comment_size = comment_brand = None

            # Use comment data if available, otherwise use title data
            price = comment_price if comment_price is not None else title_price
            year = comment_year if comment_year is not None else title_year
            ref_number = comment_ref if comment_ref is not None else title_ref
            size = comment_size if comment_size is not None else title_size
            brand = comment_brand if comment_brand is not None else title_brand

            logger.info(f"Final data - Price: {price}, Year: {year}, Ref: {ref_number}, Size: {size}, Brand: {brand}")

            try:
                cursor.execute('''
                    INSERT INTO watches 
                    (title, price, year, reference_number, size, brand, link)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (submission.title, price, year, ref_number, size, brand, submission.url))
                
                posts_added += 1
                logger.info(f"Added post {posts_added}/10: {submission.title}")
                
                # Send notification only for Rolex posts
                if brand == 'Rolex':
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