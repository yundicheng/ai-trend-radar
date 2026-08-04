"""Collection script for AI Trend Radar.

This is the "glue" file: it connects fetcher.py (talks to GitHub) with
database.py (talks to SQLite). Run it whenever you want to save a fresh
snapshot of AI-related repos for today.

Usage:
    python collect.py
"""

from datetime import date

from database import init_db, insert_repos
from fetcher import fetch_trending_repos


def get_today() -> str:
    """Return today's date as a string like '2026-08-03'.

    Every row in a snapshot gets tagged with this same string, so later
    the app can ask the database "give me everything collected on this
    date" -- which is exactly what powers the date-comparison feature.
    """
    return date.today().isoformat()


def collect_snapshot(limit_per_topic: int = 50) -> list[dict]:
    """Fetch fresh repo data from GitHub and save it as today's snapshot.

    This function does three things, in order:
      1. Make sure the database table exists (safe to call every time --
         it does nothing if the table is already there).
      2. Ask fetcher.py for the current list of AI-related repos.
      3. Save that list into SQLite, tagged with today's date.

    It returns the list of repos that were saved, so whoever called this
    function (the block below, or later the Streamlit app) can print or
    display a summary without needing to query the database again.
    """
    init_db()

    today = get_today()
    repos = fetch_trending_repos(limit_per_topic=limit_per_topic)
    insert_repos(repos, collected_date=today)

    return repos


if __name__ == "__main__":
    # Run with: python collect.py
    # This performs one real collection: fetch from GitHub, save to SQLite,
    # then print a short summary so you can see it worked.
    saved_repos = collect_snapshot()
    print(f"Saved {len(saved_repos)} repos for {get_today()}")
    for repo in saved_repos[:5]:
        print(f"  {repo['stars']:>6}  {repo['full_name']}")
