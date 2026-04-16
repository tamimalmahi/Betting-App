import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    # Render-er PostgreSQL URL sometimes starts with "postgres://" 
    # but psycopg2 needs "postgresql://"
    url = DATABASE_URL
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)


def init_db():
    conn = get_db()
    c = conn.cursor()

    # CREATE TABLE IF NOT EXISTS — data DELETE hobe na, shudhu table na thakle banabe
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT DEFAULT '',
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

    conn.commit()
    conn.close()
