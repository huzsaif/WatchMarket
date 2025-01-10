from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route("/")
def home():
    connection = sqlite3.connect("watches.db")
    cursor = connection.cursor()

    cursor.execute("SELECT title, price, year, reference_number, size, brand, link FROM watches")
    watches = cursor.fetchall()

    return render_template("index.html", watches=watches)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)