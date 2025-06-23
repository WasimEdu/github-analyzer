# 🔍 GitHub Profile Analyzer

A Flask-based web app that analyzes GitHub profiles using the GitHub API. It provides insights such as public repository count, total stars, followers, and most-used programming languages—all presented with a clean, responsive interface.

---

## 🚀 Features

- 🔎 Search any GitHub username
- 📁 View public repositories
- ⭐ See total stars received
- 👥 Get followers count
- 🧠 Discover top 5 most-used languages
- 🎨 Clean Bootstrap-powered UI

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, Bootstrap 5
- **API**: GitHub REST API (v3)
- **Libraries**: `requests`, `jinja2`

---

## ⚙️ Getting Started

Follow the steps below to run the project locally:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/github-profile-analyzer.git
cd github-profile-analyzer

# 2. Create and activate a virtual environment
python -m venv venv
# Activate on Windows:
venv\Scripts\activate
# Activate on macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the Flask app
python app.py
