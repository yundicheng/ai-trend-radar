"""Comparison logic for AI Trend Radar.

This file only does pandas data-wrangling -- it never talks to SQLite or
Streamlit. It takes two snapshots (as DataFrames, already loaded by
database.py) and figures out what changed between them.
"""

import pandas as pd


def compare_snapshots(older_repos: pd.DataFrame, newer_repos: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compare two snapshots and split the result into three DataFrames.

    `older_repos` and `newer_repos` are DataFrames shaped like the output
    of database.get_repos_by_date() -- one row per repo, with a
    `full_name` column (e.g. "huggingface/transformers") that uniquely
    identifies a repo.

    Returns a dict with three keys:
      "new"     -- repos present in `newer_repos` but not `older_repos`
      "removed" -- repos present in `older_repos` but not `newer_repos`
      "common"  -- repos present in both, with star_change/fork_change columns

    We match repos by `full_name` because a repo can be renamed but its
    full_name is what GitHub's search API gives us consistently, and it's
    unique (unlike the short `name`, which two different repos could share).
    """
    merged = older_repos.merge(
        newer_repos,
        on="full_name",
        how="outer",
        suffixes=("_old", "_new"),
        indicator=True,  # adds a "_merge" column: "left_only", "right_only", or "both"
    )

    new_repos = merged[merged["_merge"] == "right_only"]
    removed_repos = merged[merged["_merge"] == "left_only"]
    common_repos = merged[merged["_merge"] == "both"].copy()
    common_repos["star_change"] = common_repos["stars_new"] - common_repos["stars_old"]
    common_repos["fork_change"] = common_repos["forks_new"] - common_repos["forks_old"]

    return {
        "new": _select_and_rename(new_repos, suffix="_new"),
        "removed": _select_and_rename(removed_repos, suffix="_old"),
        "common": common_repos[
            [
                "full_name",
                "language_new",
                "stars_old",
                "stars_new",
                "star_change",
                "forks_old",
                "forks_new",
                "fork_change",
                "url_new",
            ]
        ].rename(columns={"language_new": "language", "url_new": "url"}),
    }


def _select_and_rename(df: pd.DataFrame, suffix: str) -> pd.DataFrame:
    """Pick the columns we care about for a one-sided (new/removed) result.

    After merging, columns that existed in both snapshots get a suffix
    like "_old" or "_new" (e.g. "language_new"). This helper picks the
    relevant suffixed columns and strips the suffix back off, so the
    result reads like a normal repo table again.
    """
    columns = ["full_name", f"language{suffix}", f"stars{suffix}", f"forks{suffix}", f"url{suffix}"]
    return df[columns].rename(columns=lambda c: c.replace(suffix, ""))


if __name__ == "__main__":
    # A tiny manual test you can run with: python analysis.py
    # Two small made-up snapshots -- no database involved -- just to prove
    # compare_snapshots() correctly sorts repos into new/removed/common.
    older = pd.DataFrame(
        [
            {"full_name": "octocat/stays", "language": "Python", "stars": 100, "forks": 10, "url": "https://x"},
            {"full_name": "octocat/removed-repo", "language": "Go", "stars": 50, "forks": 5, "url": "https://y"},
        ]
    )
    newer = pd.DataFrame(
        [
            {"full_name": "octocat/stays", "language": "Python", "stars": 120, "forks": 8, "url": "https://x"},
            {"full_name": "octocat/new-repo", "language": "Rust", "stars": 30, "forks": 2, "url": "https://z"},
        ]
    )

    result = compare_snapshots(older, newer)
    print("New repos:\n", result["new"], "\n")
    print("Removed repos:\n", result["removed"], "\n")
    print("Common repos:\n", result["common"])
