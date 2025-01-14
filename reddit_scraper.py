import praw
import os
import logging
import sqlite3
import smtplib
from email.mime.text import MIMEText
import re

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
            client_id="796nqtKpzmGTsgPaL8v9eA",
            client_secret="JqQTxcEkhFduFzwmXG-ND2cV9UXeWw",
            user_agent="WatchExchange Scraper v1.0"
        )
        
        subreddit = reddit.subreddit('watchexchange')
        logger.info("Fetching new posts from r/watchexchange")
        
        conn = sqlite3.connect('watches.db')
        cursor = conn.cursor()
        
        post_count = 0
        for post in subreddit.new(limit=10):
            title = post.title
            
            # Extract initial data from title
            price = extract_price(title)
            size = extract_size(title)
            brand = extract_brand(title)
            
            # Get author's comment for additional details
            post.comments.replace_more(limit=0)
            author_comment = None
            for comment in post.comments:
                if comment.author == post.author:
                    author_comment = comment.body
                    logger.info(f"Found author comment for post: {title}")
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
            
            # Log extracted information
            logger.info(f"Extracted data - Title: {title}")
            logger.info(f"Price: ${price if price else 'Not found'}")
            logger.info(f"Size: {size}mm" if size else "Size: Not found")
            logger.info(f"Brand: {brand if brand else 'Not found'}")
            
            # Check if post already exists
            cursor.execute('SELECT id FROM posts WHERE link = ?', (post_link,))
            if cursor.fetchone() is None:
                # Insert into database
                cursor.execute('''
                    INSERT INTO posts (title, price, size, brand, link)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, price, size, brand, post_link))
                
                post_count += 1
                
                # Send notification if it's a Rolex post
                if brand == 'Rolex':
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
    
    # Split into lines and process each line
    for line in text.split('\n'):
        # Look for $ pattern
        if '$' in line:
            try:
                # Find the $ and get the subsequent number
                dollar_index = line.find('$')
                price_text = ''
                for char in line[dollar_index + 1:]:
                    if char.isdigit() or char == ',':
                        price_text += char
                    elif char == '.':
                        break
                    elif price_text and not char.isdigit():
                        break
                if price_text:
                    return float(price_text.replace(',', ''))
            except ValueError:
                continue
        
        # Look for price keywords
        price_keywords = ['price:', 'asking', 'asking price:', 'price is']
        for keyword in price_keywords:
            if keyword in line:
                try:
                    # Extract numbers from the line
                    numbers = ''.join(char for char in line if char.isdigit() or char == ',')
                    if numbers:
                        return float(numbers.replace(',', ''))
                except ValueError:
                    continue
    
    return None

def extract_size(text):
    """Extract watch size from text"""
    text = text.lower()
    
    # Common size patterns
    patterns = [
        r'(\d{2})mm',  # matches: 40mm
        r'(\d{2}) mm', # matches: 40 mm
        r'size:?\s*(\d{2})',  # matches: size: 40 or size 40
        r'(\d{2})\s*millimeter',  # matches: 40 millimeter
    ]
    
    for line in text.split('\n'):
        # Look for common size indicators
        if 'mm' in line or 'size' in line or 'case' in line:
            # Extract all numbers from the line
            numbers = [int(n) for n in re.findall(r'\d+', line)]
            # Filter likely case sizes (between 20 and 60mm)
            valid_sizes = [n for n in numbers if 20 <= n <= 60]
            if valid_sizes:
                return valid_sizes[0]
    
    return None

def extract_brand(text):
    """Extract watch brand from text"""
    # List of common watch brands (add more as needed)
    brands = {
        'rolex': 'Rolex',
        'omega': 'Omega',
        'seiko': 'Seiko',
        'tudor': 'Tudor',
        'cartier': 'Cartier',
        'iwc': 'IWC',
        'panerai': 'Panerai',
        'patek': 'Patek Philippe',
        'audemars': 'Audemars Piguet',
        'ap': 'Audemars Piguet',
        'breitling': 'Breitling',
        'tag': 'Tag Heuer',
        'heuer': 'Tag Heuer',
        'longines': 'Longines',
        'tissot': 'Tissot',
        'oris': 'Oris',
        'zenith': 'Zenith',
        'hamilton': 'Hamilton',
        'grand seiko': 'Grand Seiko',
        'gs': 'Grand Seiko'
    }
    
    text = text.lower()
    
    # First try to match exact brand names
    for brand_key, brand_name in brands.items():
        if brand_key in text:
            return brand_name
            
    return None