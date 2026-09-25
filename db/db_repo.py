import json
import sqlite3

from db.db_conn import get_connection


def save_email_history(email_data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO email_history(
            email_id,
            thread_id,
            sender,
            subject,
            category,
            priority,
            action_items,
            meeting_details,
            draft_response
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            email_data.get("email_id"),
            email_data.get("thread_id"),
            email_data.get("sender"),
            email_data.get("subject"),
            email_data.get("category"),
            email_data.get("priority"),
            json.dumps(email_data.get("parsed_action_items", [])),
            json.dumps(email_data.get("parsed_meeting", {})),
            email_data.get("parsed_draft", "")
        )
    )

    conn.commit()
    conn.close()


def save_action(
    thread_id: str,
    action_type: str,
    action_value: str
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO email_actions(
            thread_id,
            action_type,
            action_value
        )
        VALUES (?, ?, ?)
        """,
        (
            thread_id,
            action_type,
            action_value
        )
    )

    conn.commit()
    conn.close()


def get_all_emails():
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM email_history
    ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return [dict(row) for row in rows]


def get_email_by_id(thread_id: str):
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM email_history
        WHERE thread_id = ?
        """,
        (thread_id,)
    )

    row = cursor.fetchone()

    conn.close()
    email = dict(row)

    email["parsed_action_items"] = json.loads(
        email["action_items"]
    )

    email["parsed_meeting"] = json.loads(
        email["meeting_details"]
    )

    email["parsed_draft"] = email["draft_response"]

    return email 



def get_actions_by_email(thread_id: str):
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM email_actions
        WHERE thread_id = ?
        ORDER BY created_at DESC
        """,
        (thread_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return [dict(row) for row in rows]