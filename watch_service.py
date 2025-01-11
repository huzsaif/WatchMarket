import subprocess
import time
from datetime import datetime

def run_scraper():
    while True:
        print(f"\nStarting scraper at {datetime.now()}")
        try:
            # Run the scraper script
            subprocess.run(["python", "reddit_scraper.py"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Scraper crashed with error: {e}")
        except Exception as e:
            print(f"Error running scraper: {e}")
        
        print("Waiting 60 seconds before restarting...")
        time.sleep(60)

if __name__ == "__main__":
    run_scraper() 