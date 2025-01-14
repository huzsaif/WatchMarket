from flask import Flask, render_template, jsonify
from reddit_scraper import get_database_posts
import os  # We need this for Render deployment

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/posts')
def get_posts():
    posts = get_database_posts()
    return jsonify(posts)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Let Render set the port
    app.run(host='0.0.0.0', port=port)