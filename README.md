# AI Trend Radar

A beginner-friendly portfolio project that tracks emerging AI and open-source
trends by collecting GitHub repository data into daily snapshots, then
displaying it as a dashboard.

This is an MVP: it collects data, stores it, and visualizes it. It does not
yet generate AI-written insights, compare across dates, or run on a schedule
(see [Current limitations](#current-limitations) below).

## What it does

1. Searches GitHub for repositories tagged with AI-related topics
   (`artificial-intelligence`, `machine-learning`, `deep-learning`, `llm`).
2. Saves each repo's name, description, language, stars, forks, topics, and
   URL into a local SQLite database, tagged with the date it was collected.
3. Displays that data in a Streamlit dashboard: overview metrics, a
   searchable/sortable table, and a language-distribution chart.

## Architecture

The project is split into small, single-purpose files. Each one only knows
about the files below it in this list -- `app.py` never talks to GitHub, and
`fetcher.py` never talks to SQLite:

```
fetcher.py  ── talks to the GitHub Search API, returns plain Python dicts
    │
    ▼
database.py ── the only file that talks to SQLite (create table, insert, read)
    │
    ▼
collect.py  ── glue: calls fetcher.py, then database.py, to save one snapshot
    │
    ▼
app.py      ── reads from database.py and renders the Streamlit dashboard
```

`collect.py` and `app.py` never run at the same time by default -- collection
is a manual step you run whenever you want fresh data, and the dashboard just
displays whatever is already saved.

### File-by-file

| File | Responsibility |
|---|---|
| `database.py` | Creates the `repo_snapshots` SQLite table; inserts rows; reads rows back by date. |
| `fetcher.py` | Calls the GitHub Search API and converts the response into the dict shape `database.py` expects. |
| `collect.py` | Wires `fetcher.py` and `database.py` together: fetch today's data, save it as today's snapshot. |
| `app.py` | The Streamlit dashboard. Reads the latest snapshot and displays metrics, a table, and a chart. |
| `requirements.txt` | The Python packages the project depends on. |

### Data storage

All data lives in one SQLite table, `repo_snapshots`, in `data/trend_radar.db`
(created automatically on first run). Every row is tagged with a
`collected_date`, and running `collect.py` again adds a **new** batch of rows
rather than overwriting old ones -- so the database naturally accumulates a
history of snapshots over time, one day at a time. The `data/` folder is not
committed to git, since it's generated output rather than source code.

## Setup

Requires Python 3.10+.

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Collect a snapshot of current AI-related repos from GitHub
python collect.py

# 4. Launch the dashboard
streamlit run app.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`).

### Optional: raise the GitHub rate limit

Without any authentication, GitHub allows 10 search requests per minute,
which is enough for this project's needs. If you hit rate limits, you can
set a [personal access token](https://github.com/settings/tokens) as an
environment variable before running `collect.py`:

```bash
export GITHUB_TOKEN=your_token_here
```

No token is required to run the project.

## Current limitations

This MVP intentionally does not include:

- **Date comparison** -- the database supports storing multiple days of
  snapshots, but the dashboard only displays the latest one so far. A
  "compare two dates" view is planned once real multi-day data exists.
- **Automatic/scheduled collection** -- `collect.py` must be run manually.
  There is no daily cron job or background scheduler.
- **AI-generated trend analysis** -- no LLM is used anywhere in this
  project yet. All analysis is plain counting/sorting with pandas.
- **Multiple data sources** -- only the GitHub Search API is used. No
  Hacker News, Reddit, arXiv, etc.
- **User accounts, email subscriptions, or payments** -- this is a
  single-user, local tool with no authentication layer.
- **Deployment** -- the app currently runs locally only.

## Known rough edges

- GitHub star counts occasionally include anomalies (spam repos, gamed
  stars) -- the dashboard doesn't attempt to filter these out.
- The language chart groups repos with no listed language under "Unknown"
  rather than excluding them.
