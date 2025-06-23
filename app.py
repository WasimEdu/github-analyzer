from flask import Flask, render_template,  request
import requests

app = Flask(__name__)

GITHUB_API = "https://api.github.com/users/"

@app.route('/', methods=['GET', 'POST'])

def index():
    if request.method == 'POST':
        username = request.form('username')
        user_url = f"{GITHUB_API}{username}"
        repo_url = f"{user_url}/repos"

        user_data = requests.get(user_url).json()
        repo_data = requests.get(repo_url).json()

        if "message" in user_data and user_data ["message"] == "Not Found":
            return render_template('index.html', error = "User not found")
        

    languages = {}
    for repo in repo_data:
        lang = repo.get('languges')
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    return render_template('profile.html', user = user_data, repos = repo_data, languages = languages)
    return render_template('index.html')

