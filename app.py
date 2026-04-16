from flask import Flask, render_template, request, redirect, session, flash, jsonify
from db import get_db, init_db
import os
import random

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret_dev_key_change_in_production")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect("/games")
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
            return redirect("/games")
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
        c.execute("SELECT id FROM users WHERE username=%s", (user,))
        if c.fetchone():
            conn.close()
            flash("Username already taken.", "danger")
            return render_template("register.html")
        c.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (user, pw))
        conn.commit()
        conn.close()
        flash("Account created! Please login.", "success")
        return redirect("/")
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ─── Games Lobby (Main Page after login) ─────────────────────────────────────

@app.route("/games")
def games():
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    row = c.fetchone()
    balance = row[0] if row else 0

    # Active rooms per game type
    c.execute("""
        SELECT id, game_type, status, bet_amount,
               (SELECT COUNT(*) FROM game_players WHERE room_id=game_rooms.id) as player_count
        FROM game_rooms WHERE status IN ('waiting','running')
        ORDER BY created_at DESC LIMIT 20
    """)
    rooms = c.fetchall()
    conn.close()
    return render_template("games.html", balance=balance, rooms=rooms)


# ─── Coin Flip (Multiplayer) ──────────────────────────────────────────────────

@app.route("/game/coinflip/create", methods=["POST"])
def coinflip_create():
    if "user" not in session:
        return redirect("/")
    bet = int(request.form.get("bet_amount", 0))
    if bet <= 0:
        flash("Invalid bet amount.", "danger")
        return redirect("/games")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    bal = c.fetchone()[0]
    if bet > bal:
        conn.close()
        flash("Insufficient balance.", "danger")
        return redirect("/games")
    c.execute("INSERT INTO game_rooms (game_type, bet_amount, max_players) VALUES ('coinflip', %s, 10) RETURNING id", (bet,))
    room_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return redirect(f"/game/room/{room_id}")


@app.route("/game/dice/create", methods=["POST"])
def dice_create():
    if "user" not in session:
        return redirect("/")
    bet = int(request.form.get("bet_amount", 0))
    if bet <= 0:
        flash("Invalid bet amount.", "danger")
        return redirect("/games")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    bal = c.fetchone()[0]
    if bet > bal:
        conn.close()
        flash("Insufficient balance.", "danger")
        return redirect("/games")
    c.execute("INSERT INTO game_rooms (game_type, bet_amount, max_players) VALUES ('dice', %s, 10) RETURNING id", (bet,))
    room_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return redirect(f"/game/room/{room_id}")


@app.route("/game/colorbet/create", methods=["POST"])
def colorbet_create():
    if "user" not in session:
        return redirect("/")
    bet = int(request.form.get("bet_amount", 0))
    if bet <= 0:
        flash("Invalid bet amount.", "danger")
        return redirect("/games")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    bal = c.fetchone()[0]
    if bet > bal:
        conn.close()
        flash("Insufficient balance.", "danger")
        return redirect("/games")
    c.execute("INSERT INTO game_rooms (game_type, bet_amount, max_players) VALUES ('colorbet', %s, 10) RETURNING id", (bet,))
    room_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return redirect(f"/game/room/{room_id}")


# ─── Game Room ────────────────────────────────────────────────────────────────

@app.route("/game/room/<int:room_id>")
def game_room(room_id):
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM game_rooms WHERE id=%s", (room_id,))
    room = c.fetchone()
    if not room:
        conn.close()
        flash("Room not found.", "danger")
        return redirect("/games")

    c.execute("""
        SELECT username, bet_amount, choice, result, payout
        FROM game_players WHERE room_id=%s ORDER BY joined_at
    """, (room_id,))
    players = c.fetchall()

    # Check if current user already joined
    c.execute("SELECT * FROM game_players WHERE room_id=%s AND username=%s", (room_id, session["user"]))
    already_joined = c.fetchone()

    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    bal_row = c.fetchone()
    balance = bal_row[0] if bal_row else 0

    conn.close()
    return render_template("game_room.html",
                           room=room, players=players,
                           already_joined=already_joined,
                           balance=balance,
                           username=session["user"])


@app.route("/game/room/<int:room_id>/join", methods=["POST"])
def join_room(room_id):
    if "user" not in session:
        return redirect("/")
    choice = request.form.get("choice")
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM game_rooms WHERE id=%s AND status='waiting'", (room_id,))
    room = c.fetchone()
    if not room:
        conn.close()
        flash("Room is not available.", "danger")
        return redirect("/games")

    bet = room[4]  # bet_amount
    c.execute("SELECT balance FROM users WHERE username=%s", (session["user"],))
    bal = c.fetchone()[0]
    if bet > bal:
        conn.close()
        flash("Insufficient balance.", "danger")
        return redirect(f"/game/room/{room_id}")

    # Check already joined
    c.execute("SELECT id FROM game_players WHERE room_id=%s AND username=%s", (room_id, session["user"]))
    if c.fetchone():
        conn.close()
        flash("You already joined this room.", "warning")
        return redirect(f"/game/room/{room_id}")

    # Check max players
    c.execute("SELECT COUNT(*) FROM game_players WHERE room_id=%s", (room_id,))
    count = c.fetchone()[0]
    if count >= room[3]:  # max_players
        conn.close()
        flash("Room is full.", "danger")
        return redirect("/games")

    # Deduct bet from balance
    c.execute("UPDATE users SET balance = balance - %s WHERE username=%s", (bet, session["user"]))
    c.execute("INSERT INTO game_players (room_id, username, bet_amount, choice) VALUES (%s, %s, %s, %s)",
              (room_id, session["user"], bet, choice))
    conn.commit()
    conn.close()
    return redirect(f"/game/room/{room_id}")


@app.route("/game/room/<int:room_id>/start", methods=["POST"])
def start_game(room_id):
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM game_rooms WHERE id=%s AND status='waiting'", (room_id,))
    room = c.fetchone()
    if not room:
        conn.close()
        flash("Cannot start game.", "danger")
        return redirect(f"/game/room/{room_id}")

    c.execute("SELECT COUNT(*) FROM game_players WHERE room_id=%s", (room_id,))
    count = c.fetchone()[0]
    if count < 2:
        conn.close()
        flash("Need at least 2 players to start.", "warning")
        return redirect(f"/game/room/{room_id}")

    game_type = room[1]

    # Determine result
    if game_type == "coinflip":
        result = random.choice(["heads", "tails"])
    elif game_type == "dice":
        result = str(random.randint(1, 6))
    elif game_type == "colorbet":
        result = random.choice(["red", "green", "blue"])
    else:
        result = "unknown"

    # Get all players
    c.execute("SELECT id, username, bet_amount, choice FROM game_players WHERE room_id=%s", (room_id,))
    players = c.fetchall()

    winners = [p for p in players if p[3] == result]
    total_pool = sum(p[2] for p in players)

    if winners:
        share = total_pool // len(winners)
        for p in players:
            if p[3] == result:
                # Winner gets share
                c.execute("UPDATE game_players SET result='won', payout=%s WHERE id=%s", (share, p[0]))
                c.execute("UPDATE users SET balance = balance + %s WHERE username=%s", (share, p[1]))
            else:
                c.execute("UPDATE game_players SET result='lost', payout=0 WHERE id=%s", (p[0],))
    else:
        # No winners — house keeps pot (all lose)
        for p in players:
            c.execute("UPDATE game_players SET result='lost', payout=0 WHERE id=%s", (p[0],))

    c.execute("UPDATE game_rooms SET status='finished', result=%s, ended_at=NOW() WHERE id=%s",
              (result, room_id))
    conn.commit()
    conn.close()
    return redirect(f"/game/room/{room_id}")


# ─── Dashboard (Deposit/Withdraw) ────────────────────────────────────────────

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
        try:
            amount = int(request.form.get("amount", 0))
        except ValueError:
            flash("Invalid amount.", "danger")
            conn.close()
            return redirect("/dashboard")

        if amount <= 0:
            flash("Amount must be greater than 0.", "danger")
            conn.close()
            return redirect("/dashboard")

        if req_type in ("deposit", "withdraw"):
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


# ─── Profile ──────────────────────────────────────────────────────────────────

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        c.execute("UPDATE users SET email=%s, phone=%s WHERE username=%s",
                  (email, phone, session["user"]))
        conn.commit()
        flash("Profile updated!", "success")

    c.execute("SELECT balance, email, phone FROM users WHERE username=%s", (session["user"],))
    row = c.fetchone()
    balance = row[0] if row else 0
    email = row[1] if row else ""
    phone = row[2] if row else ""

    # Game stats
    c.execute("""
        SELECT COUNT(*), SUM(payout), 
               SUM(CASE WHEN result='won' THEN 1 ELSE 0 END)
        FROM game_players WHERE username=%s
    """, (session["user"],))
    stats = c.fetchone()
    conn.close()

    return render_template("profile.html",
                           username=session["user"],
                           balance=balance, email=email, phone=phone,
                           total_games=stats[0] or 0,
                           total_won=stats[2] or 0,
                           total_earnings=stats[1] or 0)


# ─── History ─────────────────────────────────────────────────────────────────

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
    c.execute("SELECT id, username, type, amount FROM transactions WHERE status='Pending' ORDER BY timestamp DESC")
    requests_list = c.fetchall()
    c.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
    total_balance = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    conn.close()

    return render_template("admin_panel.html",
                           requests=requests_list,
                           total_balance=total_balance,
                           total_users=total_users)


@app.route("/admin/action/<int:txn_id>/<status>")
def admin_action(txn_id, status):
    if "admin" not in session:
        return redirect("/admin")
    if status not in ("Approved", "Rejected"):
        return redirect("/admin")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, type, amount FROM transactions WHERE id=%s AND status='Pending'", (txn_id,))
    txn = c.fetchone()
    if txn:
        username, txn_type, amount = txn
        if status == "Approved":
            if txn_type == "deposit":
                c.execute("UPDATE users SET balance = balance + %s WHERE username=%s", (amount, username))
            elif txn_type == "withdraw":
                c.execute("SELECT balance FROM users WHERE username=%s", (username,))
                user_row = c.fetchone()
                if user_row and user_row[0] >= amount:
                    c.execute("UPDATE users SET balance = balance - %s WHERE username=%s", (amount, username))
                else:
                    status = "Rejected"
        c.execute("UPDATE transactions SET status=%s WHERE id=%s", (status, txn_id))
        conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/admin/users")
def admin_users():
    if "admin" not in session:
        return redirect("/admin")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, email, phone, balance FROM users ORDER BY id")
    users = c.fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)


@app.route("/admin/user/<int:user_id>", methods=["GET", "POST"])
def admin_user_detail(user_id):
    if "admin" not in session:
        return redirect("/admin")
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_balance":
            new_balance = int(request.form.get("balance", 0))
            c.execute("UPDATE users SET balance=%s WHERE id=%s", (new_balance, user_id))
            conn.commit()
            flash("Balance updated!", "success")
        elif action == "update_info":
            email = request.form.get("email", "")
            phone = request.form.get("phone", "")
            password = request.form.get("password", "")
            if password:
                c.execute("UPDATE users SET email=%s, phone=%s, password=%s WHERE id=%s",
                          (email, phone, password, user_id))
            else:
                c.execute("UPDATE users SET email=%s, phone=%s WHERE id=%s",
                          (email, phone, user_id))
            conn.commit()
            flash("User info updated!", "success")
        elif action == "delete_user":
            c.execute("DELETE FROM game_players WHERE username=(SELECT username FROM users WHERE id=%s)", (user_id,))
            c.execute("DELETE FROM transactions WHERE username=(SELECT username FROM users WHERE id=%s)", (user_id,))
            c.execute("DELETE FROM users WHERE id=%s", (user_id,))
            conn.commit()
            conn.close()
            flash("User deleted.", "warning")
            return redirect("/admin/users")

    c.execute("SELECT id, username, email, phone, balance FROM users WHERE id=%s", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        flash("User not found.", "danger")
        return redirect("/admin/users")

    c.execute("SELECT type, amount, status, timestamp FROM transactions WHERE username=%s ORDER BY timestamp DESC", (user[1],))
    transactions = c.fetchall()

    c.execute("""
        SELECT gr.game_type, gp.bet_amount, gp.choice, gp.result, gp.payout, gr.result as game_result, gr.created_at
        FROM game_players gp
        JOIN game_rooms gr ON gp.room_id = gr.id
        WHERE gp.username=%s ORDER BY gr.created_at DESC
    """, (user[1],))
    game_history = c.fetchall()

    conn.close()
    return render_template("admin_user_detail.html",
                           user=user,
                           transactions=transactions,
                           game_history=game_history)


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


if __name__ == "__main__":
    init_db()
    app.run(debug=False)
