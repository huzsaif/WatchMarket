import os
from flask import Flask, render_template, send_from_directory
import sqlite3

app = Flask(__name__)

@app.route('/OneSignalSDKWorker.js')
def serve_onesignal_worker():
    return send_from_directory('static', 'OneSignalSDKWorker.js')

@app.route('/OneSignalSDK.sw.js')
def serve_onesignal_sdk():
    return send_from_directory('static', 'OneSignalSDKWorker.js')

@app.route("/")
def home():
    try:
        conn = sqlite3.connect("watches.db")
        cursor = conn.cursor()
        # Modified query to sort by newest first
        cursor.execute('''
            SELECT title, price, year, reference_number, size, brand, link 
            FROM watches 
            ORDER BY ROWID DESC 
            LIMIT 10
        ''')
        watches = cursor.fetchall()
        return render_template("index.html", watches=watches)
    except Exception as e:
        print(f"Database error: {e}")
        return f"Error accessing database: {str(e)}"
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)