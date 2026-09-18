#!/usr/bin/env python3
"""
Automated GitHub Profile Projects Updater.
Fetches repository metadata and dynamically updates the Core Projects section in README.md.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib import request, error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GITHUB_USER = os.environ.get("GITHUB_USER", "Ish-xo")
README_PATH = "README.md"
CONFIG_PATH = "profile-projects.json"

DEFAULT_CONFIG = {
    "featured": [
        "Veda",
        "rag-pipeline",
        "Traffic_intersection_intelligent_system",
        "Pothole-Detection-Telemetry-System",
    ],
    "excluded": [
        "Ish-xo",
        "Pong_game",
        "BST-Algorithm-Visualizer-",
        "MDM-Embeded-Arduino-Projects",
        "hhgoa26-frameingoa",
        "tab_graveyard",
    ],
    "limit": 4,
    "min_size_kb": 50,
    "custom_titles": {},
    "custom_emojis": {},
    "custom_descriptions": {},
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
                merged = DEFAULT_CONFIG.copy()
                merged.update(cfg)
                return merged
        except Exception as exc:
            print(f"Warning: Failed to load {CONFIG_PATH}: {exc}. Using default configuration.")
    return DEFAULT_CONFIG

def fetch_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-projects-bot",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def fetch_all_repos():
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&page={page}&sort=pushed"
        try:
            batch = fetch_json(url)
        except error.HTTPError as exc:
            if exc.code == 404:
                break
            raise

        if not batch:
            break

        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return repos

def compute_impact_score(repo):
    stars = repo.get("stargazers_count", 0)
    size = repo.get("size", 0)  # size in KB
    score = stars * 100 + min(size / 50.0, 50.0)

    # Activity bonus based on last push
    pushed_at_str = repo.get("pushed_at") or repo.get("updated_at")
    if pushed_at_str:
        try:
            pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - pushed_at).days
            if days_ago <= 30:
                score += 40
            elif days_ago <= 90:
                score += 25
            elif days_ago <= 180:
                score += 10
        except Exception:
            pass

    if repo.get("description"):
        score += 15
    if repo.get("topics"):
        score += len(repo.get("topics", [])) * 5

    return score

def infer_emoji(repo_name, language, topics, custom_emojis):
    if repo_name in custom_emojis:
        return custom_emojis[repo_name]

    text = f"{repo_name} {language or ''} {' '.join(topics or [])}".lower()
    if any(k in text for k in ["traffic", "vehicle", "car", "road", "pothole"]):
        return "🚦"
    if any(k in text for k in ["rag", "ai", "llm", "neural", "yolo", "gpt", "model"]):
        return "🤖"
    if any(k in text for k in ["flutter", "dart", "mobile", "android", "ios", "health"]):
        return "📱"
    if any(k in text for k in ["campus", "map", "navigation", "route", "graph"]):
        return "🗺️"
    if any(k in text for k in ["web", "react", "next", "vue", "frontend", "html"]):
        return "🌐"
    if any(k in text for k in ["api", "server", "fastapi", "backend", "express"]):
        return "⚡"
    if any(k in text for k in ["security", "auth", "crypto"]):
        return "🔒"
    return "🚀"

def format_title(repo_name, custom_titles):
    if repo_name in custom_titles:
        return custom_titles[repo_name]
    # Clean up hyphens and underscores, apply Title Case
    cleaned = repo_name.replace("-", " ").replace("_", " ").strip()
    return cleaned.title()

def select_projects(repos, config):
    featured_names = config.get("featured", [])
    excluded_names = set(config.get("excluded", []))
    min_size_kb = config.get("min_size_kb", 50)
    limit = config.get("limit", 4)

    repo_map = {}
    eligible_repos = []

    for r in repos:
        name = r.get("name")
        # STRICT FILTER: No private repos, no forks, no self repo, no excluded repos
        if r.get("private", False):
            continue
        if r.get("fork", False):
            continue
        if name == GITHUB_USER:
            continue
        if name in excluded_names:
            continue

        repo_map[name] = r

        # Exclude small/trivial repos unless explicitly pinned in featured
        if name in featured_names or r.get("size", 0) >= min_size_kb:
            eligible_repos.append(r)

    selected = []
    selected_names = set()

    # 1. Add featured repos first in order
    for fname in featured_names:
        if fname in repo_map and fname not in selected_names:
            selected.append(repo_map[fname])
            selected_names.add(fname)
            if len(selected) >= limit:
                break

    # 2. Fill remaining slots with highest impact eligible repos
    if len(selected) < limit:
        non_featured = [r for r in eligible_repos if r["name"] not in selected_names]
        ranked = sorted(non_featured, key=compute_impact_score, reverse=True)
        for r in ranked:
            selected.append(r)
            selected_names.add(r["name"])
            if len(selected) >= limit:
                break

    return selected

def build_projects_markdown(selected_repos, config):
    custom_titles = config.get("custom_titles", {})
    custom_emojis = config.get("custom_emojis", {})
    custom_descriptions = config.get("custom_descriptions", {})

    lines = ["<!-- CORE_PROJECTS_START -->"]

    for repo in selected_repos:
        name = repo.get("name")
        html_url = repo.get("html_url") or f"https://github.com/{GITHUB_USER}/{name}"
        title = format_title(name, custom_titles)
        emoji = infer_emoji(name, repo.get("language"), repo.get("topics"), custom_emojis)

        # Use GitHub repo description if present; fallback to custom description
        raw_desc = repo.get("description")
        if raw_desc and raw_desc.strip():
            desc = raw_desc.strip()
        else:
            desc = custom_descriptions.get(name, "An impactful open-source software project.")

        lines.append(f"* {emoji} **[{title}]({html_url})**: {desc}")

    lines.append("<!-- CORE_PROJECTS_END -->")
    return "\n".join(lines)

def update_readme(projects_markdown):
    with open(README_PATH, "r", encoding="utf-8") as fh:
        content = fh.read()

    pattern = r"<!-- CORE_PROJECTS_START -->.*?<!-- CORE_PROJECTS_END -->"
    if re.search(pattern, content, re.DOTALL):
        updated = re.sub(pattern, projects_markdown, content, count=1, flags=re.DOTALL)
    else:
        marker = "### 🛠️ Core Projects"
        if marker not in content:
            raise RuntimeError("Core Projects section marker not found in README.md")
        # Replace existing bullet list under ### 🛠️ Core Projects until next divider '---'
        section_pattern = r"(### 🛠️ Core Projects\s*\n)(.*?)(?=\n---)"
        if re.search(section_pattern, content, re.DOTALL):
            updated = re.sub(
                section_pattern,
                r"\1\n" + projects_markdown + "\n",
                content,
                count=1,
                flags=re.DOTALL,
            )
        else:
            updated = re.sub(
                r"(### 🛠️ Core Projects\s*\n)",
                r"\1\n" + projects_markdown + "\n",
                content,
                count=1,
                flags=re.DOTALL,
            )

    with open(README_PATH, "w", encoding="utf-8") as fh:
        fh.write(updated)

def main():
    config = load_config()
    repos = fetch_all_repos()
    selected = select_projects(repos, config)
    projects_md = build_projects_markdown(selected, config)
    update_readme(projects_md)
    print("Updated Core Projects in README.md:")
    print(projects_md)

if __name__ == "__main__":
    main()
