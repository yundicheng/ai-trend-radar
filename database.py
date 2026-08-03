"""Database layer for AI Trend Radar.

This file is the ONLY place in the project that talks to SQLite directly.
Every other file (the fetcher, the Streamlit app) will call the functions
below instead of writing SQL itself. That way, if we ever change how data
is stored, we only have to change this one file.
"""

import os
import sqlite3

# Where the database file lives on disk. It's a plain file, not a server.
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "trend_radar.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Open a connection to the SQLite file, creating the folder if needed.

    sqlite3.connect() will create the .db file itself if it doesn't exist,
    but it will NOT create missing folders, so we make the "data" folder
    ourselves first.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    # row_factory tells sqlite3 to return rows we can access by column name
    # (e.g. row["stars"]) instead of just by position (e.g. row[5]).
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create the repo_snapshots table if it doesn't already exist.

    Call this once when the app starts. It's safe to call every time --
    "CREATE TABLE IF NOT EXISTS" does nothing if the table is already there.
    """
    conn = get_connection(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repo_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            full_name TEXT NOT NULL,
            description TEXT,
            language TEXT,
            stars INTEGER NOT NULL,
            forks INTEGER NOT NULL,
            topics TEXT,
            url TEXT NOT NULL,
            collected_date TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def insert_repos(repos: list[dict], collected_date: str, db_path: str = DB_PATH) -> None:
    """Save a batch of repos as one day's snapshot.

    `repos` is a list of plain dictionaries, one per repository, e.g.:
        {
            "name": "transformers",
            "full_name": "huggingface/transformers",
            "description": "...",
            "language": "Python",
            "stars": 130000,
            "forks": 26000,
            "topics": ["nlp", "deep-learning"],   # a list of strings
            "url": "https://github.com/huggingface/transformers",
        }

    `collected_date` is a string like "2026-08-03" that tags every row in
    this batch, so later we can ask "show me the data from this date."

    This function doesn't call any API -- it just writes rows that are
    already in memory. The fetcher (built later) is responsible for
    producing this list of dictionaries.
    """
    conn = get_connection(db_path)
    rows = [
        (
            repo["name"],
            repo["full_name"],
            repo.get("description"),
            repo.get("language"),
            repo["stars"],
            repo["forks"],
            # SQLite has no list type, so we join topics into one string,
            # e.g. ["nlp", "deep-learning"] -> "nlp,deep-learning"
            ",".join(repo.get("topics", [])),
            repo["url"],
            collected_date,
        )
        for repo in repos
    ]
    conn.executemany(
        """
        INSERT INTO repo_snapshots
            (name, full_name, description, language, stars, forks, topics, url, collected_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()


def get_snapshot_dates(db_path: str = DB_PATH) -> list[str]:
    """Return every distinct collection date we have data for, newest first.

    Used by the Streamlit app to fill the "pick a date" dropdowns.
    """
    conn = get_connection(db_path)
    cursor = conn.execute(
        "SELECT DISTINCT collected_date FROM repo_snapshots ORDER BY collected_date DESC"
    )
    dates = [row["collected_date"] for row in cursor.fetchall()]
    conn.close()
    return dates


def get_repos_by_date(collected_date: str, db_path: str = DB_PATH) -> list[dict]:
    """Return all repo rows collected on a given date, as a list of dicts.

    We convert sqlite3.Row objects to plain dicts so the rest of the app
    (pandas, Streamlit) doesn't need to know anything about SQLite.
    """
    conn = get_connection(db_path)
    cursor = conn.execute(
        "SELECT * FROM repo_snapshots WHERE collected_date = ? ORDER BY stars DESC",
        (collected_date,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    # A tiny manual test you can run with:  python database.py
    # It creates the table, inserts one fake repo, then reads it back --
    # just to prove the functions above actually work together.
    init_db()

    fake_repo = {
        "name": "example-repo",
        "full_name": "octocat/example-repo",
        "description": "A fake repo used to test the database layer.",
        "language": "Python",
        "stars": 42,
        "forks": 7,
        "topics": ["ai", "example"],
        "url": "https://github.com/octocat/example-repo",
    }
    insert_repos([fake_repo], collected_date="2026-08-03")

    print("Dates in the database:", get_snapshot_dates())
    print("Repos on 2026-08-03:")
    for repo in get_repos_by_date("2026-08-03"):
        print(" ", repo)
