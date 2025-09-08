from flask import Flask, render_template_string, request
import subprocess
import os
import re
import json
from datetime import datetime

app = Flask(__name__)
CONFIG_FILE = "git_config.json"

# --- Git helpers ---
def run_command(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip(), result.stderr.strip() if result.returncode != 0 else None

def detect_repo_url(local_path):
    git_config_path = os.path.join(local_path, ".git", "config")
    if os.path.exists(git_config_path):
        with open(git_config_path, "r") as f:
            match = re.search(r'url\s*=\s*(.+)', f.read())
            if match:
                return match.group(1).strip()
    return None

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"projects": []}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def push_to_github(local_path, repo_url, commit_message):
    if not os.path.exists(os.path.join(local_path, ".git")):
        run_command("git init", cwd=local_path)
        run_command(f"git remote add origin {repo_url}", cwd=local_path)

    run_command("git add .", cwd=local_path)
    run_command(f'git commit -m "{commit_message}"', cwd=local_path)
    run_command("git branch -M main", cwd=local_path)
    out, err = run_command("git push -u origin main", cwd=local_path)

    return out if out else "", err if err else ""

# --- Web UI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GitHub Auto Push</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
  <div class="w-full max-w-2xl bg-white shadow-lg rounded-2xl p-8">
    <h2 class="text-2xl font-bold text-center text-gray-800 mb-6">🚀 GitHub Auto Push Dashboard</h2>
    
    <form method="post" class="space-y-4">
      <div>
        <label class="block text-gray-600 font-medium mb-1">Select Project</label>
        <select name="project" class="w-full p-2 border rounded-lg focus:outline-none focus:ring focus:ring-indigo-300">
          <option value="new">➕ Add New Project</option>
          {% for p in projects %}
            <option value="{{loop.index0}}" {% if selected==loop.index0 %}selected{% endif %}>{{p.local_path}} → {{p.repo_url}}</option>
          {% endfor %}
        </select>
      </div>

      <div>
        <label class="block text-gray-600 font-medium mb-1">Local Project Path</label>
        <input type="text" name="local_path" value="{{local_path}}" 
               class="w-full p-2 border rounded-lg focus:outline-none focus:ring focus:ring-indigo-300" required>
      </div>
      
      <div>
        <label class="block text-gray-600 font-medium mb-1">Repository URL</label>
        <input type="text" name="repo_url" value="{{repo_url}}" 
               class="w-full p-2 border rounded-lg focus:outline-none focus:ring focus:ring-indigo-300" required>
      </div>
      
      <div>
        <label class="block text-gray-600 font-medium mb-1">Commit Message</label>
        <input type="text" name="commit_message" placeholder="Leave blank for auto" 
               class="w-full p-2 border rounded-lg focus:outline-none focus:ring focus:ring-indigo-300">
      </div>
      
      <div class="flex space-x-2">
        <button type="submit" name="action" value="push" 
                class="flex-1 bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 transition">
          Push to GitHub
        </button>
        <button type="submit" name="action" value="save" 
                class="flex-1 bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition">
          Save Project
        </button>
      </div>
    </form>
    
    {% if message %}
      <div class="mt-6 p-4 rounded-lg {% if '✅' in message %}bg-green-100 text-green-700{% else %}bg-red-100 text-red-700{% endif %}">
        <pre class="whitespace-pre-wrap">{{message}}</pre>
      </div>
    {% endif %}
  </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    config = load_config()
    projects = config.get("projects", [])
    local_path, repo_url, message = "", "", ""
    selected = None

    if request.method == "POST":
        action = request.form["action"]
        project_choice = request.form["project"]
        local_path = request.form["local_path"].strip()
        repo_url = request.form["repo_url"].strip()
        commit_message = request.form["commit_message"].strip()

        if not commit_message:
            commit_message = f"Auto update on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        if action == "save":
            if project_choice == "new":
                projects.append({"local_path": local_path, "repo_url": repo_url})
            else:
                idx = int(project_choice)
                projects[idx] = {"local_path": local_path, "repo_url": repo_url}
            save_config({"projects": projects})
            message = "✅ Project saved successfully"
        elif action == "push":
            out, err = push_to_github(local_path, repo_url, commit_message)
            message = f"✅ Success:\\n{out}" if not err else f"❌ Error:\\n{err}"

        # Update selected project
        if project_choice != "new":
            selected = int(project_choice)

    return render_template_string(HTML_TEMPLATE, projects=projects, local_path=local_path, repo_url=repo_url, message=message, selected=selected)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
