import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    url = DATABASE_URL
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        balance INTEGER DEFAULT 100
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        username TEXT NOT NULL,
        type TEXT NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT DEFAULT 'Pending',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Multiplayer game rooms (Coin Flip, Dice Roll, Color Bet)
    c.execute("""CREATE TABLE IF NOT EXISTS game_rooms (
        id SERIAL PRIMARY KEY,
        game_type TEXT NOT NULL,
        status TEXT DEFAULT 'waiting',
        max_players INTEGER DEFAULT 10,
        bet_amount INTEGER DEFAULT 0,
        result TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ended_at TIMESTAMP DEFAULT NULL
    )""")

    # Each player's bet in a room
    c.execute("""CREATE TABLE IF NOT EXISTS game_players (
        id SERIAL PRIMARY KEY,
        room_id INTEGER REFERENCES game_rooms(id),
        username TEXT NOT NULL,
        bet_amount INTEGER NOT NULL,
        choice TEXT DEFAULT NULL,
        payout INTEGER DEFAULT 0,
        result TEXT DEFAULT 'pending',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()
