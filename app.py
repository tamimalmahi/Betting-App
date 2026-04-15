from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import random

from db import get_db, init_db
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

init_db()

# -------- LOGIN --------
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
        else:
            flash("Invalid username or password!", "danger")

    return render_template("login.html")

# -------- REGISTER --------
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

# -------- DASHBOARD --------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    balance = c.fetchone()[0]

    message = ""

    if request.method == "POST":
        game = request.form.get("game")
        bet = int(request.form.get("bet", 0))

        if bet <= 0 or bet > balance:
            message = "Invalid bet!"
        else:
            if game == "dice":
                dice = random.randint(1, 6)
                if dice >= 4:
                    balance += bet
                    message = f"Dice {dice} → WIN"
                else:
                    balance -= bet
                    message = f"Dice {dice} → LOSE"

            elif game == "guess":
                guess = int(request.form.get("guess", 0))
                number = random.randint(1, 5)

                if guess == number:
                    balance += bet * 2
                    message = f"Correct! ({number})"
                else:
                    balance -= bet
                    message = f"Wrong! ({number})"

            c.execute("UPDATE users SET balance=%s WHERE username=%s",
                      (balance, session["user"]))
            c.execute("INSERT INTO transactions (username, type, amount) VALUES (%s, %s, %s)",
                      (session["user"], "game", bet))

            conn.commit()

    conn.close()

    return render_template("dashboard.html", balance=balance, message=message)

# -------- DEPOSIT --------
@app.route("/deposit", methods=["POST"])
def deposit():
    if "user" not in session:
        return redirect("/")

    amount = int(request.form["amount"])

    conn = get_db()
    c = conn.cursor()

    c.execute("UPDATE users SET balance = balance + %s WHERE username=%s",
              (amount, session["user"]))
    c.execute("INSERT INTO transactions (username, type, amount) VALUES (%s, %s, %s)",
              (session["user"], "deposit", amount))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# -------- WITHDRAW --------
@app.route("/withdraw", methods=["POST"])
def withdraw():
    if "user" not in session:
        return redirect("/")

    amount = int(request.form["amount"])

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    balance = c.fetchone()[0]

    if amount <= balance:
        c.execute("UPDATE users SET balance = balance - %s WHERE username=%s",
                  (amount, session["user"]))
        c.execute("INSERT INTO transactions (username, type, amount) VALUES (%s, %s, %s)",
                  (session["user"], "withdraw", amount))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# -------- PROFILE --------
@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT username, balance FROM users WHERE username=%s", (session["user"],))
    user_data = c.fetchone()

    conn.close()

    return render_template("profile.html", username=user_data[0], balance=user_data[1])

# -------- HISTORY --------
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT type, amount, id FROM transactions WHERE username=%s ORDER BY id DESC", (session["user"],))
    transactions = c.fetchall()

    conn.close()

    return render_template("history.html", transactions=transactions)

# -------- ADMIN --------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form["username"] == config.ADMIN_USERNAME and request.form["password"] == config.ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        else:
            return render_template("admin.html", error="Invalid admin credentials!")

    if "admin" not in session:
        return render_template("admin.html")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT SUM(balance) FROM users")
    total_balance = c.fetchone()[0]

    c.execute("SELECT * FROM transactions")
    data = c.fetchall()

    conn.close()

    return render_template("transactions.html", total_balance=total_balance, data=data)

# -------- LOGOUT --------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run()
