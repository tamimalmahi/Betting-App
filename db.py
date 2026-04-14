import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Ei line duita database ke clear korbe jate notun column add hote pare
    c.execute("DROP TABLE IF EXISTS transactions CASCADE")
    c.execute("DROP TABLE IF EXISTS users CASCADE")

    # Notun column (email, dob) shoho table toiri
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        email TEXT,
        dob TEXT,
        balance INTEGER DEFAULT 100
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS transactions(
        id SERIAL PRIMARY KEY,
        username TEXT,
        type TEXT,
        amount INTEGER,
        status TEXT DEFAULT 'Pending',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()
