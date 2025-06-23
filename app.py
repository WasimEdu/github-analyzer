from flask import Flask, render_template, request
import requests
import os
from collections import Counter

app = Flask(__name__)

GITHUB_API_URL = "https://api.github.com/users/{}"
REPOS_API_URL = "https://api.github.com/users/{}/repos?per_page=100"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"]
        user_data = requests.get(GITHUB_API_URL.format(username)).json()

        if "message" in user_data and user_data["message"] == "Not Found":
            return render_template("index.html", error="User not found")

        repos = requests.get(REPOS_API_URL.format(username)).json()

        total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
        top_languages = Counter(repo.get("language") for repo in repos if repo.get("language"))
        top_languages = dict(top_languages.most_common(5))

        profile_info = {
            "name": user_data.get("name", username),
            "username": username,
            "avatar_url": user_data.get("avatar_url"),
            "public_repos": user_data.get("public_repos"),
            "followers": user_data.get("followers"),
            "stars": total_stars,
            "top_languages": top_languages
        }

        return render_template("result.html", profile=profile_info)

    return render_template("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
