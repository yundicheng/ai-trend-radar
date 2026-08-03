"""GitHub data-fetching layer for AI Trend Radar.

This file is the ONLY place in the project that talks to the GitHub API.
It has no idea that SQLite exists -- it just returns plain Python
dictionaries, in the exact shape that database.insert_repos() expects.
"""

import os
import time

import requests

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"

# Topics we search for. Repos on GitHub can be tagged with "topics" like
# "machine-learning" or "llm" -- these are the ones we consider AI-related.
DEFAULT_TOPICS = [
    "artificial-intelligence",
    "machine-learning",
    "deep-learning",
    "llm",
]

# GitHub's Search API allows only 10 requests per minute without an access
# token, so we pause briefly between requests to avoid getting rate-limited.
SECONDS_BETWEEN_REQUESTS = 2


def _build_headers() -> dict:
    """Build the HTTP headers sent with every request.

    GitHub lets you attach a personal access token via a GITHUB_TOKEN
    environment variable to raise the rate limit (10/min -> 30/min for
    search). This is entirely optional -- if the variable isn't set, we
    just make unauthenticated requests, which is fine for this project.
    """
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _search_repositories(query: str, limit: int = 10) -> list[dict]:
    """Run one GitHub Search API query and return the raw JSON items.

    `query` uses GitHub's search syntax, e.g. "topic:machine-learning".
    `limit` caps how many repos come back (GitHub calls this per_page).
    """
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": limit,
    }
    response = requests.get(
        GITHUB_SEARCH_URL, headers=_build_headers(), params=params, timeout=10
    )
    response.raise_for_status()  # raises an exception if GitHub returned an error
    return response.json()["items"]


def _to_repo_dict(item: dict) -> dict:
    """Convert one raw GitHub API item into our simplified repo shape.

    GitHub's API response has dozens of fields we don't need (avatar URLs,
    permissions, license info, etc). This function keeps only the fields
    our database layer cares about, using the exact key names that
    database.insert_repos() expects.
    """
    return {
        "name": item["name"],
        "full_name": item["full_name"],
        "description": item.get("description"),
        "language": item.get("language"),
        "stars": item["stargazers_count"],
        "forks": item["forks_count"],
        "topics": item.get("topics", []),
        "url": item["html_url"],
    }


def fetch_trending_repos(
    topics: list[str] = DEFAULT_TOPICS, limit_per_topic: int = 10
) -> list[dict]:
    """Fetch AI-related repos for each topic and return one combined list.

    We run one search per topic (GitHub's query syntax doesn't let you OR
    several topics together in a single call), then merge all the results
    and remove duplicates -- a repo tagged both "llm" and "machine-learning"
    would otherwise show up twice.

    The returned list is sorted by star count, highest first. This is the
    list you pass straight into database.insert_repos().
    """
    repos_by_full_name: dict[str, dict] = {}

    for i, topic in enumerate(topics):
        if i > 0:
            time.sleep(SECONDS_BETWEEN_REQUESTS)  # stay under GitHub's rate limit

        items = _search_repositories(query=f"topic:{topic}", limit=limit_per_topic)
        for item in items:
            repo = _to_repo_dict(item)
            repos_by_full_name[repo["full_name"]] = repo  # dedupe by full_name

    all_repos = list(repos_by_full_name.values())
    all_repos.sort(key=lambda repo: repo["stars"], reverse=True)
    return all_repos


if __name__ == "__main__":
    # A tiny manual test you can run with: python fetcher.py
    # It fetches real data from GitHub and prints a short summary --
    # no database involved yet.
    repos = fetch_trending_repos(limit_per_topic=5)
    print(f"Fetched {len(repos)} unique repos\n")
    for repo in repos[:10]:
        print(f"{repo['stars']:>6}  {repo['full_name']}  ({repo['language']})")
