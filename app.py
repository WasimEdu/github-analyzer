from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import ceil
from urllib.parse import urlparse

import os

import requests
from flask import Flask, jsonify, redirect, render_template, request, url_for


app = Flask(__name__)

GITHUB_API_ROOT = "https://api.github.com"
REQUEST_TIMEOUT = 10
RECENT_ACTIVITY_DAYS = 90


class GitHubAnalyzerError(Exception):
    """Raised when GitHub data cannot be fetched or interpreted safely."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def get_github_token():
    return os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")


def get_github_session():
    session = requests.Session()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-profile-analyzer",
    }
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    session.headers.update(headers)
    return session


def fetch_json(url, params=None):
    session = get_github_session()

    try:
        response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise GitHubAnalyzerError(
            "GitHub could not be reached right now. Please try again in a moment.",
            status_code=503,
        ) from exc

    if response.status_code == 404:
        raise GitHubAnalyzerError(
            "User not found. Please check the username and try again.",
            status_code=404,
        )

    if response.status_code == 403:
        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "")
        is_rate_limited = (
            rate_limit_remaining == "0" 
            or "rate limit" in response.text.lower()
            or "rate limited" in response.text.lower()
        )
        
        if is_rate_limited:
            reset_at = response.headers.get("X-RateLimit-Reset")
            reset_hint = ""
            if reset_at:
                try:
                    reset_time = datetime.fromtimestamp(int(reset_at), tz=timezone.utc)
                    reset_hint = f" Limit resets around {reset_time.strftime('%I:%M %p UTC')}."
                except (TypeError, ValueError):
                    reset_hint = ""

            token_hint = (
                ""
                if get_github_token()
                else " Add a GitHub token in the GITHUB_TOKEN environment variable to raise the limit."
            )
            raise GitHubAnalyzerError(
                "GitHub API rate limit reached."
                f"{reset_hint}{token_hint}",
                status_code=429,
            )
        
        raise GitHubAnalyzerError(
            "GitHub API access forbidden. This may be due to rate limiting or missing permissions.",
            status_code=403,
        )

    if response.status_code >= 400:
        raise GitHubAnalyzerError(
            f"GitHub returned an unexpected response ({response.status_code}).",
            status_code=response.status_code,
        )

    try:
        return response.json()
    except ValueError as exc:
        raise GitHubAnalyzerError("GitHub returned unreadable data.", status_code=502) from exc


def fetch_all_repositories(username, public_repo_count=0):
    if public_repo_count == 0:
        return []

    repositories = []
    total_pages = ceil(public_repo_count / 100) if public_repo_count else None
    page = 1

    while total_pages is None or page <= total_pages:
        page_data = fetch_json(
            f"{GITHUB_API_ROOT}/users/{username}/repos",
            params={"per_page": 100, "page": page, "sort": "updated"},
        )

        if not isinstance(page_data, list):
            raise GitHubAnalyzerError("Repository data could not be processed.")

        repositories.extend(page_data)

        if total_pages is None and len(page_data) < 100:
            break

        page += 1

    return repositories


def safe_external_link(value):
    if not value:
        return None

    parsed = urlparse(value if "://" in value else f"https://{value}")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return parsed.geturl()


def iso_to_datetime(value):
    if not value:
        return None

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def compact_number(value):
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def build_stat(label, value, accent):
    return {"label": label, "value": value, "compact_value": compact_number(value), "accent": accent}


def build_insights(user_data, repositories, language_counts, total_stars, recent_repo_count):
    insights = []

    if language_counts:
        language, repo_count = language_counts.most_common(1)[0]
        insights.append(
            f"{language} is the strongest signal in this portfolio, showing up across {repo_count} repositories."
        )

    if total_stars:
        insights.append(
            f"The projects have earned {total_stars} total stars, which shows visible community interest."
        )

    if recent_repo_count:
        insights.append(
            f"{recent_repo_count} repositories were updated in the last {RECENT_ACTIVITY_DAYS} days, which suggests active maintenance."
        )

    original_projects = sum(1 for repo in repositories if not repo.get("fork"))
    if original_projects:
        insights.append(
            f"{original_projects} public repositories are original builds rather than forks, which strengthens the project signal."
        )

    if user_data.get("hireable"):
        insights.append("The profile is marked as open to work, which fits nicely with a portfolio-ready presentation.")

    return insights[:4]


@lru_cache(maxsize=64)
def analyze_profile(username):
    normalized_username = username.strip().lower()
    if not normalized_username:
        raise GitHubAnalyzerError("Please enter a GitHub username.", status_code=400)

    user_data = fetch_json(f"{GITHUB_API_ROOT}/users/{normalized_username}")
    public_repo_count = user_data.get("public_repos", 0)
    repositories = fetch_all_repositories(normalized_username, public_repo_count)

    language_counts = Counter(repo.get("language") for repo in repositories if repo.get("language"))
    total_language_repos = sum(language_counts.values()) or 1
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repositories)
    total_forks = sum(repo.get("forks_count", 0) for repo in repositories)
    total_watchers = sum(repo.get("watchers_count", 0) for repo in repositories)
    original_repo_count = sum(1 for repo in repositories if not repo.get("fork"))
    forked_repo_count = sum(1 for repo in repositories if repo.get("fork"))
    archived_count = sum(1 for repo in repositories if repo.get("archived"))
    recent_threshold = datetime.now(timezone.utc) - timedelta(days=RECENT_ACTIVITY_DAYS)
    recent_repo_count = sum(
        1
        for repo in repositories
        if (iso_to_datetime(repo.get("pushed_at")) or datetime(1970, 1, 1, tzinfo=timezone.utc))
        >= recent_threshold
    )

    top_languages = [
        {
            "name": language,
            "count": count,
            "share": round((count / total_language_repos) * 100, 1),
        }
        for language, count in language_counts.most_common(6)
    ]

    ranked_repositories = sorted(
        repositories,
        key=lambda repo: (
            repo.get("stargazers_count", 0),
            repo.get("forks_count", 0),
            repo.get("watchers_count", 0),
            repo.get("updated_at", ""),
        ),
        reverse=True,
    )

    top_repositories = [
        {
            "name": repo.get("name"),
            "description": repo.get("description") or "No description provided.",
            "language": repo.get("language") or "Mixed",
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "watchers": repo.get("watchers_count", 0),
            "updated_at": iso_to_datetime(repo.get("updated_at")).strftime("%b %d, %Y")
            if iso_to_datetime(repo.get("updated_at"))
            else "Unknown",
            "url": repo.get("html_url"),
            "homepage": safe_external_link(repo.get("homepage")),
            "is_fork": bool(repo.get("fork")),
            "is_archived": bool(repo.get("archived")),
        }
        for repo in ranked_repositories[:6]
    ]

    stats = [
        build_stat("Repositories", user_data.get("public_repos", 0), "orange"),
        build_stat("Followers", user_data.get("followers", 0), "blue"),
        build_stat("Total Stars", total_stars, "green"),
        build_stat("Forks", total_forks, "gold"),
        build_stat("Watching", total_watchers, "purple"),
        build_stat("Following", user_data.get("following", 0), "teal"),
    ]

    activity_score = min(
        100,
        round(
            original_repo_count * 3
            + recent_repo_count * 4
            + min(total_stars, 120) * 0.35
            + min(user_data.get("followers", 0), 100) * 0.25
        ),
    )

    created_at = iso_to_datetime(user_data.get("created_at"))
    last_profile_update = iso_to_datetime(user_data.get("updated_at"))

    profile = {
        "name": user_data.get("name") or normalized_username,
        "username": normalized_username,
        "avatar_url": user_data.get("avatar_url"),
        "bio": user_data.get("bio") or "No bio is set on the GitHub profile yet.",
        "location": user_data.get("location"),
        "company": user_data.get("company"),
        "blog": safe_external_link(user_data.get("blog")),
        "twitter": user_data.get("twitter_username"),
        "profile_url": user_data.get("html_url"),
        "created_at": created_at.strftime("%b %Y") if created_at else "Unknown",
        "updated_at": last_profile_update.strftime("%b %d, %Y") if last_profile_update else "Unknown",
        "hireable": bool(user_data.get("hireable")),
        "stats": stats,
        "top_languages": top_languages,
        "top_repositories": top_repositories,
        "insights": build_insights(
            user_data, repositories, language_counts, total_stars, recent_repo_count
        ),
        "recent_repo_count": recent_repo_count,
        "original_repo_count": original_repo_count,
        "forked_repo_count": forked_repo_count,
        "archived_count": archived_count,
        "activity_score": activity_score,
        "generated_at": datetime.now().strftime("%b %d, %Y %I:%M %p"),
    }

    return profile


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    username = request.form.get("username", "").strip()

    if not username:
        return render_template("index.html", error="Please enter a GitHub username."), 400

    return redirect(url_for("profile_view", username=username))


@app.route("/profile/<username>", methods=["GET"])
def profile_view(username):
    try:
        profile = analyze_profile(username)
    except GitHubAnalyzerError as exc:
        return (
            render_template("index.html", error=str(exc), previous_username=username),
            exc.status_code,
        )

    return render_template("result.html", profile=profile)


@app.route("/api/profile/<username>", methods=["GET"])
def profile_api(username):
    try:
        profile = analyze_profile(username)
    except GitHubAnalyzerError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    return jsonify(profile)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
