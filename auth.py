import sqlite3
import re

def init_db():
    """Initializes the database schema for users and chats."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Table to store custom registered users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Table to maintain session histories like ChatGPT
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def validate_email_format(email):
    """Validates email formatting."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def register_user(name, email, password):
    """Registers a new administrator profile dynamically."""
    if not validate_email_format(email):
        return False, "Invalid email formatting."
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."
        
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO admin_info (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        return True, "Registration successful! Please login."
    except sqlite3.IntegrityError:
        return False, "This email is already registered."
    finally:
        conn.close()

def check_login(email, password):
    """Verifies credentials match database records."""
    if not validate_email_format(email):
        return False
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_info WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    return user is not None