from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, init_db
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

init_db()

# User Login
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"].strip()
        pw = request.form["password"].strip()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=%s", (user,))
        data = c.fetchone()
        conn.close()
        if data and check_password_hash(data[2], pw):
            session.clear()
            session["user"] = user
            return redirect(url_for("dashboard"))
        return "Invalid User Credentials"
    return render_template("login.html")

# Admin Login & Panel
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        # Space avoid korar jonno .strip() use kora hoyeche
        user = request.form.get("username", "").strip()
        pw = request.form.get("password", "").strip()
        
        if user == config.ADMIN_USERNAME and pw == config.ADMIN_PASSWORD:
            session.clear()
            session["admin"] = True
            return redirect("/admin") # Sothik hole eikhane redirect hobe
        else:
            return "Invalid Admin Credentials! <a href='/admin'>Try Again</a>"

    if "admin" in session:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, type, amount, status FROM transactions WHERE status='Pending'")
        pending = c.fetchall()
        conn.close()
        return render_template("admin_panel.html", requests=pending)

    return render_template("admin.html") # admin.html template ta login form thakbe

@app.route("/admin/action/<int:req_id>/<string:status>")
def admin_action(req_id, status):
    if not session.get("admin_logged_in"): 
        return redirect(url_for("admin"))
        
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, type, amount FROM transactions WHERE id=%s", (req_id,))
    req = c.fetchone()
    
    if req and status == "Approved":
        username, t_type, amount = req
        if t_type == "deposit":
            c.execute("UPDATE users SET balance = balance + %s WHERE username=%s", (amount, username))
        else:
            c.execute("UPDATE users SET balance = balance - %s WHERE username=%s", (amount, username))
    
    c.execute("UPDATE transactions SET status=%s WHERE id=%s", (status, req_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

# Baki route gulo (dashboard, profile, register) ager motoi thakbe...
