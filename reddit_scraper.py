import praw
import re
import sqlite3
import subprocess
import requests

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

def send_push_notification(title, link):
    headers = {
        "Authorization": f"Basic {ONESIGNAL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["All"],
        "contents": {"en": f"New Rolex Post: {title}"},
        "url": link,
    }
    response = requests.post(ONESIGNAL_API_URL, headers=headers, json=payload)
    print(f"Notification Response: {response.status_code}, {response.text}")

def save_to_db(details, title, link):
    connection = sqlite3.connect("watches.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO watches (title, price, year, reference_number, size, brand, link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, details["price"], details["year"], details["reference_number"], details["size"], details["brand"], link))

    connection.commit()
    connection.close()

    if details["brand"] == "Rolex":
        send_push_notification(title, link)

def scrape_op_responses(post):
    """Extract data from the OP's responses if it's missing in the title."""
    title_details = {
        "price": None,
        "year": None,
        "reference_number": None,
        "size": None,
        "brand": None,
    }

    # Extracting details from the title
    words = post.title.split()
    for i, word in enumerate(words):
        if word.startswith("$"):
            title_details["price"] = word.strip("$,")
        if len(word) == 4 and word.isdigit():
            title_details["year"] = word
        if len(word) in [5, 6] and word.isdigit():
            title_details["reference_number"] = word
        if "mm" in word.lower():
            title_details["size"] = word
        if word.lower() in ["rolex", "omega", "seiko", "tudor", "cartier"]:
            title_details["brand"] = word

    # If any field is still None, check the OP's responses
    if any(value is None for value in title_details.values()):
        post.comments.replace_more(limit=0)  # Expand all comments
        for comment in post.comments.list():
            if comment.author == post.author:  # Ensure it's the OP's comment
                words = comment.body.split()
                for i, word in enumerate(words):
                    if title_details["price"] is None and word.startswith("$"):
                        title_details["price"] = word.strip("$,")
                    if title_details["year"] is None and len(word) == 4 and word.isdigit():
                        title_details["year"] = word
                    if title_details["reference_number"] is None and len(word) in [5, 6] and word.isdigit():
                        title_details["reference_number"] = word
                    if title_details["size"] is None and "mm" in word.lower():
                        title_details["size"] = word

    return title_details

def scrape_watchexchange():
    subreddit = reddit.subreddit("watchexchange")

    for post in subreddit.new(limit=10):
        link = f"https://www.reddit.com{post.permalink}"
        title_details = scrape_op_responses(post)  # Extract data from title and OP's comments
        save_to_db(title_details, post.title, link)
        print(f"Processed Post: {post.title}")

if __name__ == "__main__":
    while True:
        scrape_watchexchange()
        time.sleep(3600)  # Run every hour