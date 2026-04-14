from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, init_db
import os

app = Flask(__name__)
app.secret_key = "any_secret_key_here" # Hardcoded for now

init_db()

# -------- USER REGISTER --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form.get("username", "").strip()
        raw_pw = request.form.get("password", "").strip()
        
        if not user or not raw_pw:
            return "Username and Password are required!"
            
        pw = generate_password_hash(raw_pw)
        conn = get_db()
        c = conn.cursor()
        try:
            # Email ebong DOB empty string hishebe thakbe prothome
            c.execute("INSERT INTO users (username, password, email, dob, balance) VALUES (%s, %s, %s, %s, %s)", 
                      (user, pw, "", "", 100))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except Exception as e:
            conn.close()
            return f"Registration Error: {str(e)}" # Ekhane error dekhabe keno hocche na
            
    return render_template("register.html")

# -------- USER LOGIN --------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "").strip()
        pw = request.form.get("password", "").strip()
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=%s", (user,))
        data = c.fetchone()
        conn.close()
        
        if data and check_password_hash(data[2], pw):
            session.clear()
            session["user"] = user
            return redirect(url_for("dashboard"))
        else:
            return "Invalid Login! <a href='/'>Try again</a>"
            
    return render_template("login.html")

# -------- ADMIN PANEL (HARDCODED) --------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        admin_user = request.form.get("username", "").strip()
        admin_pass = request.form.get("password", "").strip()
        
        # Sorasori check korchi jate config file-er jhamela na hoy
        if admin_user == "admin" and admin_pass == "admin123":
            session.clear()
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        else:
            return "Admin Login Failed! <a href='/admin'>Try again</a>"

    if session.get("admin_logged_in"):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, type, amount, status FROM transactions WHERE status='Pending'")
        pending = c.fetchall()
        conn.close()
        return render_template("admin_panel.html", requests=pending)
    
    return render_template("admin.html")

# -------- OTHER ROUTES --------
@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template("dashboard.html", balance=balance)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run()
