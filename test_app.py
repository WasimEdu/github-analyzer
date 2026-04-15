import os
import unittest
from unittest.mock import patch

from app import GitHubAnalyzerError, analyze_profile, app, get_github_session


class GitHubAnalyzerTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        analyze_profile.cache_clear()

    def tearDown(self):
        analyze_profile.cache_clear()

    @patch("app.fetch_json")
    def test_analyze_profile_builds_expected_metrics(self, mock_fetch_json):
        mock_fetch_json.side_effect = [
            {
                "name": "Ada Lovelace",
                "avatar_url": "https://example.com/avatar.png",
                "bio": "First programmer",
                "location": "London",
                "company": "@analytical",
                "blog": "ada.dev",
                "twitter_username": "ada",
                "html_url": "https://github.com/ada",
                "created_at": "2020-01-01T00:00:00Z",
                "updated_at": "2026-04-01T00:00:00Z",
                "public_repos": 3,
                "followers": 24,
                "following": 5,
                "hireable": True,
            },
            [
                {
                    "name": "vision-board",
                    "description": "Best project",
                    "language": "Python",
                    "stargazers_count": 14,
                    "forks_count": 3,
                    "watchers_count": 5,
                    "updated_at": "2026-04-01T00:00:00Z",
                    "pushed_at": "2026-04-01T00:00:00Z",
                    "html_url": "https://github.com/ada/vision-board",
                    "homepage": "ada.dev/vision-board",
                    "fork": False,
                    "archived": False,
                },
                {
                    "name": "signal-lab",
                    "description": "",
                    "language": "Python",
                    "stargazers_count": 6,
                    "forks_count": 1,
                    "watchers_count": 2,
                    "updated_at": "2026-03-15T00:00:00Z",
                    "pushed_at": "2026-03-15T00:00:00Z",
                    "html_url": "https://github.com/ada/signal-lab",
                    "homepage": "",
                    "fork": False,
                    "archived": False,
                },
                {
                    "name": "css-playground",
                    "description": "Frontend ideas",
                    "language": "CSS",
                    "stargazers_count": 2,
                    "forks_count": 0,
                    "watchers_count": 1,
                    "updated_at": "2025-12-01T00:00:00Z",
                    "pushed_at": "2025-12-01T00:00:00Z",
                    "html_url": "https://github.com/ada/css-playground",
                    "homepage": None,
                    "fork": True,
                    "archived": False,
                },
            ],
        ]

        profile = analyze_profile("Ada")

        self.assertEqual(profile["name"], "Ada Lovelace")
        self.assertEqual(profile["stats"][2]["value"], 22)
        self.assertEqual(profile["stats"][3]["value"], 4)
        self.assertEqual(profile["top_languages"][0]["name"], "Python")
        self.assertEqual(profile["top_repositories"][0]["name"], "vision-board")
        self.assertEqual(profile["original_repo_count"], 2)
        self.assertEqual(profile["forked_repo_count"], 1)
        self.assertTrue(profile["blog"].startswith("https://"))
        self.assertGreaterEqual(profile["activity_score"], 1)

    @patch("app.analyze_profile")
    def test_profile_route_handles_errors(self, mock_analyze_profile):
        mock_analyze_profile.side_effect = GitHubAnalyzerError("User not found.")

        response = self.client.get("/profile/missing-user")

        self.assertEqual(response.status_code, 404)
        self.assertIn(b"User not found.", response.data)

    @patch("app.analyze_profile")
    def test_api_route_returns_json(self, mock_analyze_profile):
        mock_analyze_profile.return_value = {
            "name": "Ada",
            "username": "ada",
            "stats": [],
            "top_languages": [],
            "top_repositories": [],
            "insights": [],
            "activity_score": 55,
            "generated_at": "Apr 12, 2026 03:00 PM",
        }

        response = self.client.get("/api/profile/ada")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["username"], "ada")

    def test_github_session_uses_token_when_available(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "secret-token"}, clear=False):
            session = get_github_session()

        self.assertEqual(session.headers["Authorization"], "Bearer secret-token")

    @patch("app.analyze_profile")
    def test_api_route_preserves_rate_limit_status(self, mock_analyze_profile):
        mock_analyze_profile.side_effect = GitHubAnalyzerError(
            "GitHub API rate limit reached. Add a GitHub token in the GITHUB_TOKEN environment variable to raise the limit.",
            status_code=429,
        )

        response = self.client.get("/api/profile/ada")

        self.assertEqual(response.status_code, 429)
        self.assertIn("rate limit", response.get_json()["error"].lower())


if __name__ == "__main__":
    unittest.main()
