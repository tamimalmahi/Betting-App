from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "secret123"

# DB connection
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="betting_app"
    )

# init DB
def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50),
        password VARCHAR(50),
        balance INT DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50),
        type VARCHAR(20),
        amount INT
    )
    """)

    conn.commit()
    conn.close()

# ---------------- REGISTER ----------------
@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        conn = get_db()
        c = conn.cursor()

        c.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (user, pw))
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=%s AND password=%s", (user, pw))
        data = c.fetchone()

        conn.close()

        if data:
            session["user"] = user
            return redirect("/dashboard")

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    balance = c.fetchone()[0]

    # HANDLE DEPOSIT / WITHDRAW
    if request.method == "POST":
        req_type = request.form.get("type")
        amount = int(request.form.get("amount"))

        if req_type == "deposit":
            c.execute("UPDATE users SET balance = balance + %s WHERE username=%s",
                      (amount, session["user"]))
            c.execute("INSERT INTO transactions (username, type, amount) VALUES (%s, %s, %s)",
                      (session["user"], "deposit", amount))

        elif req_type == "withdraw":
            if amount <= balance:
                c.execute("UPDATE users SET balance = balance - %s WHERE username=%s",
                          (amount, session["user"]))
                c.execute("INSERT INTO transactions (username, type, amount) VALUES (%s, %s, %s)",
                          (session["user"], "withdraw", amount))

        conn.commit()
        return redirect("/dashboard")

    conn.close()
    return render_template("dashboard.html", balance=balance)

# ---------------- ADMIN ----------------
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

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
