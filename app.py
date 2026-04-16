from flask import Flask, render_template, request, redirect, session, flash
from db import get_db, init_db
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret_dev_key_change_in_production")

# Admin credentials from environment variables (Render dashboard-e set korbe)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


@app.route("/", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect("/dashboard")

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
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        conn = get_db()
        c = conn.cursor()

        # Check if username already exists
        c.execute("SELECT id FROM users WHERE username=%s", (user,))
        existing = c.fetchone()

        if existing:
            conn.close()
            flash("Username already taken. Please choose another.", "danger")
            return render_template("register.html")

        c.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (user, pw))
        conn.commit()
        conn.close()

        flash("Account created! Please login.", "success")
        return redirect("/")

    return render_template("register.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    row = c.fetchone()
    balance = row[0] if row else 0

    if request.method == "POST":
        req_type = request.form.get("type")
        amount_str = request.form.get("amount", "0")

        try:
            amount = int(amount_str)
        except ValueError:
            flash("Invalid amount.", "danger")
            conn.close()
            return redirect("/dashboard")

        if amount <= 0:
            flash("Amount must be greater than 0.", "danger")
            conn.close()
            return redirect("/dashboard")

        if req_type in ("deposit", "withdraw"):
            # Insert as Pending — admin will approve/reject
            c.execute(
                "INSERT INTO transactions (username, type, amount, status) VALUES (%s, %s, %s, 'Pending')",
                (session["user"], req_type, amount)
            )
            conn.commit()
            flash(f"{req_type.capitalize()} request submitted! Waiting for admin approval.", "info")

        conn.close()
        return redirect("/dashboard")

    conn.close()
    return render_template("dashboard.html", balance=balance)


@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    row = c.fetchone()
    balance = row[0] if row else 0
    conn.close()

    return render_template("profile.html", username=session["user"], balance=balance)


@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT type, amount, status, timestamp FROM transactions WHERE username=%s ORDER BY timestamp DESC",
        (session["user"],)
    )
    transactions = c.fetchall()
    conn.close()

    return render_template("history.html", transactions=transactions)


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]

        if user == ADMIN_USERNAME and pw == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        else:
            return render_template("admin.html", error="Invalid admin credentials")

    if "admin" not in session:
        return render_template("admin.html", error=None)

    conn = get_db()
    c = conn.cursor()

    # Pending requests
    c.execute("SELECT id, username, type, amount FROM transactions WHERE status='Pending'")
    requests_list = c.fetchall()

    # Total balance of all users
    c.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
    total_balance = c.fetchone()[0]

    conn.close()

    return render_template("admin_panel.html", requests=requests_list, total_balance=total_balance)


@app.route("/admin/action/<int:txn_id>/<status>")
def admin_action(txn_id, status):
    if "admin" not in session:
        return redirect("/admin")

    if status not in ("Approved", "Rejected"):
        return redirect("/admin")

    conn = get_db()
    c = conn.cursor()

    # Get the transaction
    c.execute("SELECT username, type, amount FROM transactions WHERE id=%s AND status='Pending'", (txn_id,))
    txn = c.fetchone()

    if txn:
        username, txn_type, amount = txn

        if status == "Approved":
            if txn_type == "deposit":
                c.execute("UPDATE users SET balance = balance + %s WHERE username=%s", (amount, username))
            elif txn_type == "withdraw":
                # Check if user has enough balance
                c.execute("SELECT balance FROM users WHERE username=%s", (username,))
                user_row = c.fetchone()
                if user_row and user_row[0] >= amount:
                    c.execute("UPDATE users SET balance = balance - %s WHERE username=%s", (amount, username))
                else:
                    # Not enough balance — reject instead
                    status = "Rejected"

        c.execute("UPDATE transactions SET status=%s WHERE id=%s", (status, txn_id))
        conn.commit()

    conn.close()
    return redirect("/admin")


@app.route("/admin/all_transactions")
def admin_all_transactions():
    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, type, amount, status, timestamp FROM transactions ORDER BY timestamp DESC")
    data = c.fetchall()
    c.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
    total_balance = c.fetchone()[0]
    conn.close()

    return render_template("transactions.html", data=data, total_balance=total_balance)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ─── App Entry Point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=False)
