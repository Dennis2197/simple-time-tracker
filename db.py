import sqlite3
import datetime

DB_FILE = "time_tracker.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT
                )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            background_color TEXT,
            weekly_goal TEXT,
            daily_goal TEXT
        )"""
    )
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO settings (background_color, weekly_goal, daily_goal) VALUES (?, ?, ?)",
            ("#F0F0F0", "40", "8"),
        )
    conn.commit()
    conn.close()


def add_session(start_time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (start_time) VALUES (?)", (start_time,))
    conn.commit()
    conn.close()


def stop_session(end_time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM sessions WHERE end_time IS NULL ORDER BY id DESC LIMIT 1")
    result = c.fetchone()
    if result:
        session_id = result[0]
        c.execute(
            "UPDATE sessions SET end_time = ? WHERE id = ?", (end_time, session_id)
        )
        conn.commit()
    conn.close()


def fetch_sessions():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM sessions ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def fetch_sessions_by_day(date_str):
    """Return all sessions for a specific day (YYYY-MM-DD)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        SELECT * FROM sessions
        WHERE DATE(start_time) = DATE(?)
        ORDER BY start_time
    """,
        (date_str,),
    )
    rows = c.fetchall()
    conn.close()
    return rows


def update_session(session_id, new_start, new_end):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE sessions SET start_time=?, end_time=? WHERE id=?",
        (new_start, new_end, session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()


def delete_sessions_by_day(date_str):
    """Delete all sessions for a specific date (YYYY-MM-DD)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE DATE(start_time) = DATE(?)", (date_str,))
    conn.commit()
    conn.close()


def fetch_daily_totals():
    """Return dict: { 'DD.MM.YYYY': total_seconds } grouped by day."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        SELECT DATE(start_time), start_time, end_time
        FROM sessions WHERE end_time IS NOT NULL
    """
    )
    rows = c.fetchall()
    conn.close()

    daily = {}
    for row in rows:
        date_key = datetime.datetime.strptime(row[0], "%Y-%m-%d").strftime("%d.%m.%Y")
        start, end = row[1], row[2]
        start_dt = datetime.datetime.fromisoformat(start)
        end_dt = datetime.datetime.fromisoformat(end)
        diff = (end_dt - start_dt).total_seconds()
        daily[date_key] = daily.get(date_key, 0) + diff
    return daily


def get_background_color():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        SELECT background_color
        FROM settings
    """
    )
    color = c.fetchall()
    conn.close()

    return color[0][0] if color else "#F0F0F0"


def update_settings(color, weekly, daily):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO settings (id, background_color, weekly_goal, daily_goal)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            background_color=excluded.background_color,
            weekly_goal=excluded.weekly_goal,
            daily_goal=excluded.daily_goal
    """,
        (color, str(weekly), str(daily)),
    )
    conn.commit()
    conn.close()


def get_weekly_goal():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        SELECT weekly_goal
        FROM settings
    """
    )
    weekly = c.fetchall()
    conn.close()

    return weekly[0][0] if weekly else "40"


def get_daily_goal():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        SELECT daily_goal
        FROM settings
    """
    )
    daily = c.fetchall()
    conn.close()

    return daily[0][0] if daily else "8"
