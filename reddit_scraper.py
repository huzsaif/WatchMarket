import praw
import sqlite3
import re
import requests
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
        
        for post in subreddit.new(limit=10):
            if posts_added >= 10:
                break
                
            title = post.title
            post_author = post.author
            
            # Only process [wts] posts
            if '[wts]' not in title.lower() and '[wts/wtt]' not in title.lower():
                continue

            # Extract data from title first
            title_price, title_year, title_ref, title_size, title_brand = extract_data(title)
            logger.info(f"From title - Price: {title_price}, Year: {title_year}, Ref: {title_ref}, Size: {title_size}, Brand: {title_brand}")

            # Get the author's comment
            post.comments.replace_more(limit=None)
            author_comment = None
            for comment in post.comments.list():
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
                ''', (post.title, price, year, ref_number, size, brand, f"https://www.reddit.com{post.permalink}"))
                
                posts_added += 1
                logger.info(f"Added post {posts_added}/10: {post.title}")
                
                # Send notification ONLY for Rolex posts - strict check
                if brand == 'Rolex' and 'rolex' in post.title.lower():
                    logger.info(f"ROLEX ALERT: Found Rolex post!")
                    logger.info(f"Title: {post.title}")
                    logger.info(f"Price: ${price:,}" if price else "Price: Unknown")
                    logger.info(f"Link: {f'https://www.reddit.com{post.permalink}'}")
                    send_notification(post.title, price, f"https://www.reddit.com{post.permalink}", brand)
                
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

def is_rolex_post(title, brand):
    """Check if post is specifically for a Rolex watch (not Tudor)"""
    # Convert title to lowercase for case-insensitive matching
    title_lower = title.lower()
    
    # Only match actual Rolex posts, not Tudor
    if brand == "Rolex" and "tudor" not in title_lower:
        return True
        
    # For title-only matching, be more strict
    if "rolex" in title_lower and "tudor" not in title_lower:
        return True
        
    return False

def send_notification(title, price, link, *args):
    """Send email notification for Rolex posts"""
    if is_rolex_post(title, args[0] if args else None):
        try:
            # Hardcoded email configuration
            sender_email = "1.0.0watchmarket@gmail.com"  # Your Gmail
            sender_password = "orjz chpx isay darh"   # Your app password
            receiver_email = "huzietc@gmail.com" # Where to send notifications
            
            # Handle case where price might be None
            price_str = f"${price:,}" if price is not None else "Price not listed"
            
            # Create message
            msg = MIMEText(f"New Rolex listing found!\n\nTitle: {title}\nPrice: {price_str}\nLink: {link}")
            msg['Subject'] = f"Rolex Alert: {title}"
            msg['From'] = sender_email
            msg['To'] = receiver_email
            
            # Send email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
                logger.info(f"Email notification sent for: {title}")
                
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")

def get_database_posts():
    """Retrieve posts from the database"""
    try:
        conn = sqlite3.connect('watches.db')
        cursor = conn.cursor()
        
        # Get the 50 most recent posts
        cursor.execute('''
            SELECT title, price, brand, size, link 
            FROM posts 
            ORDER BY id DESC 
            LIMIT 50
        ''')
        
        # Convert to list of dictionaries
        posts = []
        for row in cursor.fetchall():
            posts.append({
                'title': row[0],
                'price': row[1],
                'brand': row[2],
                'size': row[3],
                'link': row[4]
            })
            
        conn.close()
        return posts
        
    except Exception as e:
        logger.error(f"Failed to retrieve posts from database: {str(e)}")
        return []

def init_database():
    """Initialize the database and create tables if they don't exist"""
    try:
        conn = sqlite3.connect('watches.db')
        cursor = conn.cursor()
        
        # Create posts table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                price REAL,
                brand TEXT,
                size INTEGER,
                link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")

# Call init_database when the module is loaded
init_database()

if __name__ == "__main__":
    scrape_watchexchange()