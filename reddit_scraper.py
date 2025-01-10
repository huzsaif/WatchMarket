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
ONESIGNAL_APP_ID = "1cc3bbe9-5caa-4b19-9105-2413ebb671f8"
ONESIGNAL_API_KEY = "os_v2_app_dtb3x2k4vjfrteifeqj6xntr7advhdoazo6e7bnmqfu7yp5qrsf6hqys35bodxrhibnx3amf6zniahjepvsobafptzy7oodx3v7zztq"

def scrape_watchexchange():
    # Connect to SQLite database
    conn = sqlite3.connect('watches.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watches (
            id INTEGER PRIMARY KEY,
            title TEXT,
            price TEXT,
            year TEXT,
            reference_number TEXT,
            size TEXT,
            brand TEXT,
            link TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    subreddit = reddit.subreddit("watchexchange")
    for post in subreddit.new(limit=10):
        title_details = extract_fields_from_title(post.title)
        author_response_details = extract_fields_from_author_response(post)
        merged_details = {**title_details, **author_response_details}
        save_to_db(cursor, conn, merged_details, post)

    conn.commit()
    conn.close()

def extract_fields_from_title(title):
    price = extract_price(title)
    reference_number = extract_reference_number(title)
    size = extract_size(title)
    brand = extract_brand(title)
    year = extract_year(title)

    return {
        "title": title,
        "price": price,
        "year": year,
        "reference_number": reference_number,
        "size": size,
        "brand": brand,
        "link": None  # This will be added later
    }

def extract_fields_from_author_response(post):
    for comment in post.comments:
        if comment.author == post.author:
            text = comment.body
            price = extract_price(text)
            reference_number = extract_reference_number(text)
            size = extract_size(text)
            brand = extract_brand(text)
            year = extract_year(text)

            return {
                "price": price,
                "year": year,
                "reference_number": reference_number,
                "size": size,
                "brand": brand
            }
    return {}

def extract_price(text):
    match = re.search(r'\$\s?(\d{1,3}(?:,\d{3})*|\d+)', text)
    if match:
        return match.group(0).replace(',', '')  # Ensure the full number is included
    return None

def extract_reference_number(text):
    match = re.search(r'\b\d{5,7}\b', text)
    if match:
        return match.group(0)
    return None

def extract_size(text):
    match = re.search(r'\b\d{2}mm\b', text, re.IGNORECASE)
    if match:
        return match.group(0)
    return None

def extract_brand(text):
    # Example logic to extract brand names, expand this list as needed
    brands = ["Rolex", "Omega", "Tudor", "Seiko", "Tag Heuer", "Cartier", "IWC"]
    for brand in brands:
        if brand.lower() in text.lower():
            return brand
    return None

def extract_year(text):
    current_year = datetime.utcnow().year
    match = re.search(r'\b(19[0-9]{2}|20[0-9]{2})\b', text)
    if match:
        year = int(match.group(0))
        if 1900 <= year <= current_year:  # Ensure year is within a reasonable range
            return str(year)
    return None

def save_to_db(cursor, conn, details, post):
    cursor.execute('''
        INSERT OR REPLACE INTO watches (title, price, year, reference_number, size, brand, link, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        details["title"],
        details["price"],
        details["year"],
        details["reference_number"],
        details["size"],
        details["brand"],
        f"https://www.reddit.com{post.permalink}",
        datetime.utcnow()
    ))

# Run scraper every 10 minutes
while True:
    scrape_watchexchange()
    time.sleep(600)