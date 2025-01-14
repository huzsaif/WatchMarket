import schedule
import time
from reddit_scraper import scrape_watchexchange

def job():
    scrape_watchexchange()

# Schedule job every 10 minutes
schedule.every(10).minutes.do(job)

# Run job immediately on startup
job()

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1) 