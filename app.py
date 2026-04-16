from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        balance INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        type TEXT,
        amount INTEGER
    )
    """)

    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, pw))
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pw))
        data = c.fetchone()
        conn.close()

        if data:
            session["user"] = user
            return redirect("/dashboard")

    return render_template("login.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE username=?", (session["user"],))
    balance = c.fetchone()["balance"]

    if request.method == "POST":
        req_type = request.form.get("type")
        amount = int(request.form.get("amount"))

        if req_type == "deposit":
            c.execute("UPDATE users SET balance = balance + ? WHERE username=?",
                      (amount, session["user"]))
            c.execute("INSERT INTO transactions (username, type, amount) VALUES (?, ?, ?)",
                      (session["user"], "deposit", amount))

        elif req_type == "withdraw":
            if amount <= balance:
                c.execute("UPDATE users SET balance = balance - ? WHERE username=?",
                          (amount, session["user"]))
                c.execute("INSERT INTO transactions (username, type, amount) VALUES (?, ?, ?)",
                          (session["user"], "withdraw", amount))

        conn.commit()
        return redirect("/dashboard")

    conn.close()
    return render_template("dashboard.html", balance=balance)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        if user == "admin" and pw == "1234":
            session["admin"] = True
            return redirect("/admin")

    if "admin" not in session:
        return render_template("admin.html")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions")
    data = c.fetchall()
    conn.close()

    return render_template("transactions.html", data=data)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    init_db()
    app.run()
