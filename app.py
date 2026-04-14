from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, init_db
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Application start hoyar somoy database table gulo toiri hobe
init_db()

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
            session.clear() # Purano session clear koro
            session["user"] = user
            return redirect(url_for("dashboard"))
        else:
            return "Invalid login credentials!"
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
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")

# -------- USER DASHBOARD & PROFILE --------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session: return redirect(url_for("login"))
    
    conn = get_db()
    c = conn.cursor()
    
    # Game Logic (Ager motoi thakbe)
    message = ""
    if request.method == "POST":
        # ... (Dice and Guess game logic here)
        pass

    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    balance_data = c.fetchone()
    balance = balance_data[0] if balance_data else 0
    conn.close()
    return render_template("dashboard.html", balance=balance, message=message)

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

# -------- ADMIN PANEL --------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        # Space error avoid korar jonno .strip() use kora hoyeche
        input_user = request.form["username"].strip()
        input_pass = request.form["password"].strip()
        
        if input_user == config.ADMIN_USERNAME and input_pass == config.ADMIN_PASSWORD:
            session.clear()
            session["admin"] = True
            return redirect(url_for("admin"))

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
    if "admin" not in session: return redirect(url_for("admin"))
    
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
    return redirect(url_for("admin"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
