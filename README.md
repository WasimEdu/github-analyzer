# GitHub Analyzer

GitHub Analyzer is a Flask app that turns any public GitHub profile into a polished analytics snapshot. It highlights repository traction, language focus, recent maintenance activity, and top projects through a clean, portfolio-ready interface.

## What Improved

- Shareable analysis pages with dedicated URLs like `/profile/<username>`
- JSON API endpoint at `/api/profile/<username>`
- Better GitHub API error handling, including rate-limit messaging
- Richer analytics such as activity score, repository mix, language distribution, and ranked top repositories
- A redesigned responsive UI with custom styling instead of a default Bootstrap layout
- Test coverage for the analysis workflow and core routes

## Tech Stack

- Python
- Flask
- Requests
- Jinja templates
- Custom CSS
- Python `unittest`

## Run Locally

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

## GitHub Rate Limit Note

GitHub allows only a small number of unauthenticated API requests per hour. If you want the analyzer to work reliably, set a personal access token before starting the app.

PowerShell:

```powershell
$env:GITHUB_TOKEN="your_github_token"
python app.py
```

The app will automatically use `GITHUB_TOKEN` or `GH_TOKEN` if either is present.

## Test

```bash
python -m unittest
```

## Project Highlights

- Designed as a stronger resume project with both backend and UI improvements
- Uses GitHub's REST API to analyze public user and repository data
- Includes a simple API layer so the project can grow into a dashboard, widget, or portfolio integration
