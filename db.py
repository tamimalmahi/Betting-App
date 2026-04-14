import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Purano table delete kore notun column shoho toiri koro
    c.execute("DROP TABLE IF EXISTS transactions CASCADE")
    c.execute("DROP TABLE IF EXISTS users CASCADE")
    
    c.execute("""CREATE TABLE users(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        email TEXT DEFAULT '',
        dob TEXT DEFAULT '',
        balance INTEGER DEFAULT 100
    )""")

    c.execute("""CREATE TABLE transactions(
        id SERIAL PRIMARY KEY,
        username TEXT,
        type TEXT,
        amount INTEGER,
        status TEXT DEFAULT 'Pending',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()
