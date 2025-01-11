import praw
import re
import sqlite3
import time
import requests
from datetime import datetime

# Reddit API credentials
reddit = praw.Reddit(
    client_id="796nqtKpzmGTsgPaL8v9eA",
    client_secret="JqQTxcEkhFduFzwmXG-ND2cV9UXeWw",
    user_agent="WatchTool/0.1 by zayfuh"
)

# OneSignal API credentials
ONESIGNAL_API_URL = "https://onesignal.com/api/v1/notifications"
ONESIGNAL_APP_ID = "3a92834d-ceb3-400c-8c68-73d52157b773"
ONESIGNAL_API_KEY = "os_v2_app_hkjigtoownaazddiopkscv5xonygya235bcur753ksbmknxrf5sixmu2cswdke5oildjettbfscfvny2qw4c66ewviyrmz3jm5bcc4a"

def send_notification(title, price, link):
    """Send a notification when a Rolex is found"""
    headers = {
        "accept": "application/json",
        "Authorization": "os_v2_app_hkjigtoownaazddiopkscv5xonygya235bcur753ksbmknxrf5sixmu2cswdke5oildjettbfscfvny2qw4c66ewviyrmz3jm5bcc4a",
        "content-type": "application/json"
    }
    
    # Format price nicely if it exists
    price_text = f"${price:,}" if price else "Price unknown"
    
    payload = {
        "app_id": "3a92834d-ceb3-400c-8c68-73d52157b773",
        "included_segments": ["Subscribed Users"],
        "contents": {"en": f"New Rolex Posted! {price_text}"},
        "headings": {"en": title},
        "url": link
    }
    
    try:
        response = requests.post(ONESIGNAL_API_URL, json=payload, headers=headers)
        print(f"Notification response status: {response.status_code}")
        print(f"Notification response body: {response.text}")
        if response.status_code == 200:
            print(f"Notification sent successfully for Rolex: {title}")
        else:
            print(f"Failed to send notification: {response.text}")
    except Exception as e:
        print(f"Error sending notification: {e}")

def scrape_watchexchange():
    try:
        conn = sqlite3.connect("watches.db")
    except sqlite3.DatabaseError:
        # If database is corrupted, remove it and create a new one
        import os
        try:
            os.remove("watches.db")
            print("Removed corrupted database file")
            conn = sqlite3.connect("watches.db")
        except FileNotFoundError:
            conn = sqlite3.connect("watches.db")
    
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price INTEGER,
            year INTEGER,
            reference_number TEXT,
            size INTEGER,
            brand TEXT,
            link TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Fetch the latest posts
    subreddit = reddit.subreddit("watchexchange")
    for post in subreddit.new(limit=10):
        # Extract details from the title
        title_details = extract_watch_details(post.title)
        
        # Extract details from the author's first comment
        author_comment_details = extract_author_comment_details(post)
        
        # Merge details
        combined_details = {**title_details, **{
            k: v for k, v in author_comment_details.items() if v is not None
        }}

        post_url = f"https://www.reddit.com{post.permalink}"

        # Check if the post is already in the database
        cursor.execute("SELECT * FROM watches WHERE link = ?", (post_url,))
        if cursor.fetchone():
            continue

        # Send notification if it's a Rolex
        if combined_details.get("brand") == "Rolex":
            send_notification(
                title=post.title,
                price=combined_details.get("price"),
                link=post_url
            )

        # Insert post into the database
        try:
            cursor.execute('''
                INSERT INTO watches (title, price, year, reference_number, size, brand, link, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(post.title) if post.title else None,  # Ensure title is string or None
                int(combined_details.get("price")) if combined_details.get("price") else None,  # Ensure price is int or None
                int(combined_details.get("year")) if combined_details.get("year") else None,  # Ensure year is int or None
                str(combined_details.get("reference_number")) if combined_details.get("reference_number") else None,
                int(combined_details.get("size")) if combined_details.get("size") else None,
                str(combined_details.get("brand")) if combined_details.get("brand") else None,
                str(post_url),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            continue  # Skip this post if there's an error
        except Exception as e:
            print(f"Error processing post: {e}")
            continue

    conn.commit()
    conn.close()


def extract_watch_details(text):
    details = {
        "price": None,
        "year": None,
        "reference_number": None,
        "size": None,
        "brand": None
    }

    # Split text into lines to handle section headers better
    text_lines = text.lower().split('\n')
    text_lower = text.lower()

    # First priority: Look for dollar sign followed by numbers
    # Check both the full text and individual lines after price-related headers
    dollar_price_patterns = [
        r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Basic $XXXX format
        r'(?:price|asking|sale).*?\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Price/header followed by $XXXX
        r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:shipped|conus|net|obo|or best offer)',  # $XXXX shipped/conus
    ]

    # Check each line after a price-related header
    for i, line in enumerate(text_lines):
        if any(header in line.lower() for header in ['price:', 'price', 'asking:', 'asking', 'sale:']):
            # Check the current line and next line for price
            check_lines = [text_lines[i]]
            if i + 1 < len(text_lines):
                check_lines.append(text_lines[i + 1])
            
            for check_line in check_lines:
                for pattern in dollar_price_patterns:
                    match = re.search(pattern, check_line)
                    if match:
                        try:
                            price_str = match.group(1).replace(",", "")
                            price_float = float(price_str)
                            details["price"] = int(price_float)
                            break
                        except (ValueError, AttributeError):
                            continue
                if details["price"] is not None:
                    break

    # If still no price found, try the regular full-text search
    if details["price"] is None:
        for pattern in dollar_price_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    price_str = match.group(1).replace(",", "")
                    price_float = float(price_str)
                    details["price"] = int(price_float)
                    break
                except (ValueError, AttributeError):
                    continue

    # Only if no dollar sign price was found, try other price patterns
    if details["price"] is None:
        other_price_patterns = [
            r"asking\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"price\s*(?:is|:)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"(?:^|\s)(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:shipped|conus|obo|or best offer|net|firm)"
        ]
        
        for pattern in other_price_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    price_str = match.group(1).replace(",", "")
                    price_float = float(price_str)
                    details["price"] = int(price_float)
                    break
                except (ValueError, AttributeError):
                    continue

    # Extract year (e.g., 1999, 2019, 2023, etc.)
    match = re.search(r"\b(19[0-9]{2}|20[0-9]{2})\b", text_lower)
    if match:
        details["year"] = int(match.group(1))

    # Extract reference number (4 to 7 digits), but only if the number isn't the price
    for match in re.finditer(r"\b(\d{4,7})\b", text_lower):
        potential_ref = match.group(1)
        # Don't use the number as a reference number if it's the price we found
        if details["price"] is not None and int(potential_ref) != details["price"]:
            details["reference_number"] = potential_ref
            break
        elif details["price"] is None:
            details["reference_number"] = potential_ref
            break

    # Extract size (e.g., "40mm")
    match = re.search(r"\b(\d{2,3})mm\b", text_lower)
    if match:
        details["size"] = int(match.group(1))

    # Extract brand
    for brand in ["Rolex", "Omega", "Seiko", "Tudor", "Cartier"]:
        if brand.lower() in text_lower:
            details["brand"] = brand
            break

    return details


def extract_author_comment_details(post):
    """
    Finds the first top-level comment by the post author, then 
    uses the same extraction logic (extract_watch_details).
    """
    post.comments.replace_more(limit=None)
    for comment in post.comments:
        if comment.author == post.author:
            # Use the same logic as the title by calling extract_watch_details
            return extract_watch_details(comment.body)

    # If the author made no comment or we didn't find it, return empty fields
    return {
        "price": None,
        "year": None,
        "reference_number": None,
        "size": None,
        "brand": None
    }


if __name__ == "__main__":
    while True:
        try:
            scrape_watchexchange()
            print("Sleeping for 10 minutes...")
            time.sleep(600)  # Sleep for 10 minutes
        except Exception as e:
            print(f"Error occurred: {e}")
            print("Retrying in 60 seconds...")
            time.sleep(60)