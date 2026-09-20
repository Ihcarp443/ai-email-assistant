import sqlite3

DB_NAME = "email_assistant.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE if not exists email_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id TEXT,
        thread_id TEXT,
        sender TEXT,
        subject TEXT,
        category TEXT,
        priority TEXT,
        action_items TEXT,
        meeting_details TEXT,
        draft_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT,
        action_type TEXT,
        action_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
