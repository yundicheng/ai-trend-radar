"""Streamlit dashboard for AI Trend Radar.

This file only displays data -- it never calls the GitHub API and never
writes to the database. It reads whatever is already stored in SQLite
(saved by running `python collect.py`) and renders it as a dashboard.

Run it with: streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from database import get_repos_by_date, get_snapshot_dates

st.set_page_config(page_title="AI Trend Radar", page_icon="📡", layout="wide")


@st.cache_data
def load_latest_snapshot() -> tuple[str | None, pd.DataFrame]:
    """Load the most recent snapshot from the database as a DataFrame.

    Returns (latest_date, dataframe). If nothing has been collected yet,
    latest_date is None and the dataframe is empty.

    Streamlit re-runs this whole script top-to-bottom every time you type
    in a widget (like the search box below). @st.cache_data tells Streamlit
    to remember this function's result instead of re-reading the database
    on every single keystroke.
    """
    dates = get_snapshot_dates()
    if not dates:
        return None, pd.DataFrame()

    latest_date = dates[0]  # get_snapshot_dates() already sorts newest first
    repos = get_repos_by_date(latest_date)
    return latest_date, pd.DataFrame(repos)


st.title("📡 AI Trend Radar")
st.caption("A snapshot of fast-growing AI-related repositories on GitHub.")

latest_date, df = load_latest_snapshot()

if df.empty:
    st.warning("No data yet. Run `python collect.py` first to collect a snapshot.")
    st.stop()

# --- Overview metrics -------------------------------------------------------
col1, col2 = st.columns(2)
col1.metric("Total repositories collected", len(df))
col2.metric("Latest collection date", latest_date)

st.divider()

# --- Repository table --------------------------------------------------------
st.subheader("Repositories")

search_term = st.text_input(
    "Search by name or description", placeholder="e.g. llm, agent, pytorch"
)

if search_term:
    matches_name = df["name"].str.contains(search_term, case=False, na=False)
    matches_description = df["description"].str.contains(search_term, case=False, na=False)
    filtered_df = df[matches_name | matches_description]
else:
    filtered_df = df

st.caption(f"Showing {len(filtered_df)} of {len(df)} repositories. Click a column header to sort.")

st.dataframe(
    filtered_df[["name", "language", "stars", "forks", "topics", "description", "url"]],
    hide_index=True,
    width="stretch",
    column_config={
        "url": st.column_config.LinkColumn("URL", display_text="Open ↗"),
    },
)

st.divider()

# --- Language distribution chart --------------------------------------------
st.subheader("Repositories by language")

language_counts = df["language"].fillna("Unknown").value_counts().reset_index()
language_counts.columns = ["language", "count"]

fig = px.bar(language_counts, x="language", y="count", text="count")
# One color for every bar on purpose: this chart shows a single measure
# (repo count) across categories, not several series, so there's nothing
# for per-bar colors to distinguish -- a legend-free single hue is clearer.
fig.update_traces(marker_color="#2a78d6", textposition="outside")
fig.update_layout(
    xaxis_title=None,
    yaxis_title="Repositories",
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font_color="#0b0b0b",
)
fig.update_xaxes(showgrid=False, linecolor="#c3c2b7")
fig.update_yaxes(gridcolor="#e1e0d9", zeroline=False)

st.plotly_chart(fig, width="stretch")
