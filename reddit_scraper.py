import praw
import os
import logging
import sqlite3
import smtplib
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                price REAL,
                year INTEGER,
                ref TEXT,
                size INTEGER,
                brand TEXT,
                link TEXT
            )
        ''')
        conn.commit()
        
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

def scrape_watchexchange():
    """Scrape r/watchexchange for posts"""
    logger.info("Starting scrape_watchexchange function")
    
    try:
        reddit = praw.Reddit(
            client_id=os.environ.get('796nqtKpzmGTsgPaL8v9eA'),
            client_secret=os.environ.get('JqQTxcEkhFduFzwmXG-ND2cV9UXeWw"'),
            user_agent="WatchExchange Scraper v1.0"
        )
        
        subreddit = reddit.subreddit('watchexchange')
        logger.info("Fetching new posts from r/watchexchange")
        
        conn = sqlite3.connect('watches.db')
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                price REAL,
                size INTEGER,
                brand TEXT,
                link TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        post_count = 0
        for post in subreddit.new(limit=10):
            title = post.title
            
            # Extract data from title
            price = extract_price(title)
            size = extract_size(title)
            brand = extract_brand(title)
            
            # Get author's comment
            post.comments.replace_more(limit=0)
            author_comment = None
            for comment in post.comments:
                if comment.author == post.author:
                    author_comment = comment.body
                    break
            
            # If we found author's comment, try to extract missing info
            if author_comment:
                if price is None:
                    price = extract_price(author_comment)
                if size is None:
                    size = extract_size(author_comment)
                if brand is None:
                    brand = extract_brand(author_comment)
            
            post_link = f"https://www.reddit.com{post.permalink}"
            
            # Check if post already exists
            cursor.execute('SELECT id FROM posts WHERE link = ?', (post_link,))
            if cursor.fetchone() is None:
                # Insert into database
                cursor.execute('''
                    INSERT INTO posts (title, price, size, brand, link)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, price, size, brand, post_link))
                
                post_count += 1
                logger.info(f"Added post {post_count}: {title}")
                
                # Send notification if it's a Rolex post
                if is_rolex_post(title, brand):
                    send_notification(title, price, post_link, brand)
        
        conn.commit()
        logger.info(f"Database updated successfully with {post_count} new posts")
        conn.close()
        
    except Exception as e:
        logger.error(f"Error in scrape_watchexchange: {str(e)}")
        if 'conn' in locals():
            conn.close()

def extract_price(text):
    """Extract price from text using various patterns"""
    text = text.lower()
    price = None
    
    # Common price patterns
    price_indicators = ['$', 'price:', 'asking', 'shipped']
    
    for line in text.split('\n'):
        # Look for $ pattern first
        dollar_index = line.find('$')
        if dollar_index != -1:
            # Extract numbers after $
            price_str = ''
            for char in line[dollar_index + 1:]:
                if char.isdigit() or char == ',':
                    price_str += char
                elif char == '.':
                    break  # Stop at decimal point
                elif price_str:  # If we've started collecting digits but hit non-digit
                    break
            if price_str:
                try:
                    return float(price_str.replace(',', ''))
                except ValueError:
                    continue
        
        # Look for price indicators
        for indicator in price_indicators:
            if indicator in line:
                # Find numbers in the line
                price_str = ''
                for char in line:
                    if char.isdigit() or char == ',':
                        price_str += char
                if price_str:
                    try:
                        return float(price_str.replace(',', ''))
                    except ValueError:
                        continue
    
    return price

def extract_size(text):
    """Extract watch size from text"""
    text = text.lower()
    size = None
    
    # Look for patterns like "40mm" or "40 mm"
    for line in text.split('\n'):
        if 'mm' in line:
            words = line.split()
            for i, word in enumerate(words):
                if 'mm' in word:
                    # Check if the size is in the same word (e.g., "40mm")
                    size_str = word.replace('mm', '').strip()
                    if size_str.isdigit():
                        return int(size_str)
                    # Check previous word (e.g., "40 mm")
                    elif i > 0 and words[i-1].isdigit():
                        return int(words[i-1])
    
    return size

def extract_brand(text):
    """Extract watch brand from text"""
    common_brands = [
        'Rolex', 'Omega', 'Seiko', 'Tudor', 'Tag Heuer', 'Cartier', 'IWC',
        'Patek Philippe', 'Audemars Piguet', 'Longines', 'Tissot', 'Hamilton',
        'Grand Seiko', 'Oris', 'Breitling', 'Panerai', 'Zenith', 'Sinn'
    ]
    
    text = text.lower()
    for brand in common_brands:
        if brand.lower() in text:
            return brand
    
    return None