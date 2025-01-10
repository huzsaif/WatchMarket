from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route('/')
def home():
    conn = sqlite3.connect('watches.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, price, year, reference_number, size, brand, link FROM watches ORDER BY timestamp DESC LIMIT 10")
    watches = cursor.fetchall()
    conn.close()
    return render_template('index.html', watches=watches)

if __name__ == '__main__':
    app.run(debug=True, port=5000)