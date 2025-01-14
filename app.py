from flask import Flask, render_template, jsonify
from reddit_scraper import get_database_posts
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/posts')
def get_posts():
    posts = get_database_posts()
    return jsonify(posts)