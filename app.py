from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import random
from db import get_db, init_db
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
init_db()

# Middleware: Check if logged in
def is_logged_in():
    return "user" in session

# -------- AUTH --------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=%s", (user,))
        data = c.fetchone()
        conn.close()
        if data and check_password_hash(data[2], pw):
            session["user"] = user
            return redirect("/dashboard")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pw = generate_password_hash(request.form["password"])
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (user, pw))
            conn.commit()
        except:
            return "User already exists!"
        conn.close()
        return redirect("/")
    return render_template("register.html")

# -------- USER DASHBOARD & PROFILE --------
@app.route("/dashboard")
def dashboard():
    if not is_logged_in(): return redirect("/")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template("dashboard.html", balance=balance)

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not is_logged_in(): return redirect("/")
    conn = get_db()
    c = conn.cursor()
    
    if request.method == "POST":
        email = request.form.get("email")
        dob = request.form.get("dob")
        c.execute("UPDATE users SET email=%s, dob=%s WHERE username=%s", (email, dob, session["user"]))
        conn.commit()

    c.execute("SELECT id, username, email, dob, balance FROM users WHERE username=%s", (session["user"],))
    user_data = c.fetchone()
    c.execute("SELECT type, amount, status, timestamp FROM transactions WHERE username=%s ORDER BY timestamp DESC", (session["user"],))
    history = c.fetchall()
    conn.close()
    return render_template("profile.html", user=user_data, history=history)

# Request Deposit/Withdraw
@app.route("/submit_request", methods=["POST"])
def submit_request():
    if not is_logged_in(): return redirect("/")
    req_type = request.form.get("type")
    amount = int(request.form.get("amount"))
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO transactions (username, type, amount, status) VALUES (%s, %s, %s, 'Pending')",
              (session["user"], req_type, amount))
    conn.commit()
    conn.close()
    return redirect("/profile")

# -------- ADMIN PANEL --------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form["username"] == config.ADMIN_USERNAME and request.form["password"] == config.ADMIN_PASSWORD:
            session["admin"] = True

    if "admin" not in session:
        return render_template("admin_login.html")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, type, amount, status FROM transactions WHERE status='Pending'")
    pending = c.fetchall()
    conn.close()
    return render_template("admin_panel.html", requests=pending)

@app.route("/admin/action/<int:req_id>/<string:status>")
def admin_action(req_id, status):
    if "admin" not in session: return redirect("/admin")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT username, type, amount FROM transactions WHERE id=%s", (req_id,))
    req = c.fetchone()
    
    if req and status == "Approved":
        username, t_type, amount = req
        if t_type == "deposit":
            c.execute("UPDATE users SET balance = balance + %s WHERE username=%s", (amount, username))
        elif t_type == "withdraw":
            c.execute("UPDATE users SET balance = balance - %s WHERE username=%s", (amount, username))
    
    c.execute("UPDATE transactions SET status=%s WHERE id=%s", (status, req_id))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run()
