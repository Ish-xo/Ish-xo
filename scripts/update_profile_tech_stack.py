#!/usr/bin/env python3

import json
import os
import re
import sys
from urllib import request, error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GITHUB_USER = os.environ.get("GITHUB_USER", "Ish-xo")
README_PATH = "README.md"

LANGUAGE_ALIASES = {
    "Python": "py",
    "JavaScript": "js",
    "TypeScript": "ts",
    "Dart": "dart",
    "React": "react",
    "Tailwind": "tailwind",
    "HTML": "html",
    "CSS": "css",
    "C": "c",
    "C++": "cpp",
    "Java": "java",
    "Go": "go",
    "Rust": "rust",
    "Kotlin": "kotlin",
    "C#": "cs",
    "PHP": "php",
    "Shell": "bash",
    "Dockerfile": "docker",
    "Node.js": "nodejs",
    "Next.js": "nextjs",
    "FastAPI": "fastapi",
    "Flutter": "flutter",
    "Vue": "vue",
    "Svelte": "svelte",
    "PostgreSQL": "postgresql",
    "MySQL": "mysql",
    "MongoDB": "mongodb",
    "Redis": "redis",
    "AWS": "aws",
    "Azure": "azure",
    "Nginx": "nginx",
    "Linux": "linux",
    "Git": "git",
    "GitHub": "github",
    "Visual Studio Code": "vscode",
    "Figma": "figma",
}

def fetch_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-tech-stack-bot",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def collect_languages():
    language_sizes = {}
    page = 1

    while True:
        repos_url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&page={page}"
        try:
            repos = fetch_json(repos_url)
        except error.HTTPError as exc:
            if exc.code == 404:
                break
            raise

        if not repos:
            break

        for repo in repos:
            if repo.get("fork"):
                continue
            repo_name = repo.get("name")
            if not repo_name:
                continue

            try:
                repo_languages = fetch_json(f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/languages")
            except error.HTTPError:
                continue

            for name, size in repo_languages.items():
                language_sizes[name] = language_sizes.get(name, 0) + size

        if len(repos) < 100:
            break
        page += 1

    return language_sizes

def normalize_language(language_name):
    if not language_name:
        return None

    key = language_name.strip()
    alias = LANGUAGE_ALIASES.get(key)
    if alias:
        return alias

    normalized = key.lower().replace(" ", "").replace(".", "").replace("+", "")
    if normalized == "javascript":
        return "js"
    if normalized == "typescript":
        return "ts"
    if normalized == "python":
        return "py"
    if normalized == "cplusplus":
        return "cpp"
    if normalized == "csharp":
        return "cs"
    if normalized == "nodejs":
        return "nodejs"
    if normalized == "nextjs":
        return "nextjs"
    if normalized == "html5":
        return "html"
    if normalized == "css3":
        return "css"
    if normalized == "markdown":
        return "md"
    if normalized == "powershell":
        return "powershell"
    if normalized == "shell":
        return "bash"
    return None

def build_icon_string(language_sizes):
    ranked = sorted(language_sizes.items(), key=lambda item: item[1], reverse=True)
    icons = []
    seen = set()

    for language_name, _ in ranked:
        icon = normalize_language(language_name)
        if icon and icon not in seen:
            icons.append(icon)
            seen.add(icon)
        if len(icons) >= 18:
            break

    if not icons:
        icons = ["py", "js", "ts", "dart", "react", "tailwind", "fastapi", "flutter", "c", "cpp", "java", "github", "vscode", "git", "html", "css"]

    return ",".join(icons)

def update_readme(icon_string):
    new_block = (
        "<!-- TECH_STACK_START -->\n"
        "<p align=\"center\">\n"
        f"  <img src=\"https://skillicons.dev/icons?i={icon_string}\" alt=\"My Tech Stack\" />\n"
        "</p>\n"
        "<!-- TECH_STACK_END -->"
    )

    with open(README_PATH, "r", encoding="utf-8") as fh:
        content = fh.read()

    pattern = r"<!-- TECH_STACK_START -->.*?<!-- TECH_STACK_END -->"
    if re.search(pattern, content, re.DOTALL):
        updated = re.sub(pattern, new_block, content, count=1, flags=re.DOTALL)
    else:
        marker = "### 💻 Tech Stack"
        if marker not in content:
            raise RuntimeError("Tech Stack section marker not found in README.md")
        updated = re.sub(
            r"(### 💻 Tech Stack\s*\n)",
            r"\1\n" + new_block + "\n",
            content,
            count=1,
            flags=re.DOTALL,
        )

    with open(README_PATH, "w", encoding="utf-8") as fh:
        fh.write(updated)

def main():
    language_sizes = collect_languages()
    icon_string = build_icon_string(language_sizes)
    update_readme(icon_string)
    print(f"Updated profile tech stack icons: {icon_string}")

if __name__ == "__main__":
    main()
