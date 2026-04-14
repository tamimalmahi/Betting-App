from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import os
from db import get_db, init_db
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

init_db()

# -------- LOGIN --------
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
    return render_template("login.html")

# -------- REGISTER --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"].strip()
        pw = generate_password_hash(request.form["password"].strip())
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (user, pw))
            conn.commit()
            return redirect(url_for("login"))
        except:
            return "User already exists!"
        finally:
            conn.close()
    return render_template("register.html")

# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template("dashboard.html", balance=balance)

# -------- PROFILE & HISTORY --------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session: return redirect(url_for("login"))
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

# -------- SUBMIT REQUEST --------
@app.route("/submit_request", methods=["POST"])
def submit_request():
    if "user" not in session: return redirect(url_for("login"))
    req_type = request.form.get("type")
    amount = int(request.form.get("amount"))
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO transactions (username, type, amount, status) VALUES (%s, %s, %s, 'Pending')",
              (session["user"], req_type, amount))
    conn.commit()
    conn.close()
    return redirect(url_for("profile"))

# -------- ADMIN --------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        admin_user = request.form["username"].strip()
        admin_pass = request.form["password"].strip()
        if admin_user == config.ADMIN_USERNAME and admin_pass == config.ADMIN_PASSWORD:
            session.clear()
            session["admin"] = True
            return redirect(url_for("admin"))

    if "admin" not in session:
        return render_template("admin.html")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, type, amount, status FROM transactions WHERE status='Pending'")
    pending = c.fetchall()
    conn.close()
    return render_template("admin_panel.html", requests=pending)

@app.route("/admin/action/<int:req_id>/<string:status>")
def admin_action(req_id, status):
    if "admin" not in session: return redirect(url_for("admin"))
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run()
