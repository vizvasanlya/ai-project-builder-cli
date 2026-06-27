import requests
import random
from datetime import datetime, timedelta


CURATED_TOPICS = [
    {"name": "file-organizer", "type": "cli", "desc": "CLI tool to organize files by type, date, or name", "tags": ["cli", "utility", "files"]},
    {"name": "json-transformer", "type": "tool", "desc": "Transform JSON data between formats (CSV, YAML, XML)", "tags": ["tool", "data", "converter"]},
    {"name": "env-manager", "type": "cli", "desc": "Manage .env files across multiple environments", "tags": ["cli", "devops", "env"]},
    {"name": "git-commit-helper", "type": "cli", "desc": "Generate meaningful git commit messages from changes", "tags": ["cli", "git", "ai"]},
    {"name": "code-formatter", "type": "tool", "desc": "Format code files with consistent style", "tags": ["tool", "code", "formatting"]},
    {"name": "password-generator", "type": "library", "desc": "Secure password generator with customizable rules", "tags": ["library", "security", "crypto"]},
    {"name": "markdown-pdf", "type": "tool", "desc": "Convert markdown files to PDF with styling", "tags": ["tool", "markdown", "pdf"]},
    {"name": "api-monitor", "type": "tool", "desc": "Monitor API endpoints for uptime and response time", "tags": ["tool", "api", "monitoring"]},
    {"name": "todo-cli", "type": "cli", "desc": "Command-line todo list with priorities and due dates", "tags": ["cli", "productivity", "todo"]},
    {"name": "log-analyzer", "type": "tool", "desc": "Parse and analyze application log files", "tags": ["tool", "logs", "analysis"]},
    {"name": "schema-validator", "type": "library", "desc": "Validate JSON/YAML data against schemas", "tags": ["library", "validation", "schema"]},
    {"name": "cron-helper", "type": "cli", "desc": "Build and test cron expressions with next run times", "tags": ["cli", "cron", "scheduler"]},
    {"name": "color-palette", "type": "library", "desc": "Generate harmonious color palettes from seed colors", "tags": ["library", "color", "design"]},
    {"name": "csv-analyzer", "type": "tool", "desc": "Analyze CSV files with statistics and filtering", "tags": ["tool", "csv", "data"]},
    {"name": "regex-tester", "type": "webapp", "desc": "Interactive regex pattern tester with highlighting", "tags": ["webapp", "regex", "testing"]},
    {"name": "markdown-preview", "type": "webapp", "desc": "Live markdown preview with custom themes", "tags": ["webapp", "markdown", "preview"]},
    {"name": "task-scheduler", "type": "library", "desc": "Lightweight task scheduler with cron-like syntax", "tags": ["library", "scheduler", "cron"]},
    {"name": "diff-viewer", "type": "webapp", "desc": "Visual diff viewer for comparing text files", "tags": ["webapp", "diff", "comparison"]},
    {"name": "snippet-manager", "type": "cli", "desc": "Save and search code snippets from terminal", "tags": ["cli", "snippets", "search"]},
    {"name": "health-check", "type": "tool", "desc": "Check health of multiple services and endpoints", "tags": ["tool", "health", "monitoring"]},
]


def research_trending():
    topics = []

    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f"created:>{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}",
                "sort": "stars",
                "order": "desc",
                "per_page": 10,
            },
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10,
        )

        if resp.ok:
            data = resp.json()
            for repo in data.get("items", [])[:5]:
                name = repo.get("name", "").lower().replace("-", " ").replace("_", " ")
                desc = repo.get("description", "") or ""
                topics.append({
                    "name": repo.get("name", "project"),
                    "type": _guess_type(name, desc),
                    "desc": desc[:100] or f"Inspired by {repo.get('name')}",
                    "tags": _extract_tags(name, desc),
                    "source": "github-trending",
                })
    except Exception:
        pass

    if len(topics) < 3:
        topics.extend(random.sample(CURATED_TOPICS, min(5, len(CURATED_TOPICS))))

    random.shuffle(topics)
    return topics


def pick_topic(preferences=None):
    topics = research_trending()

    if preferences:
        filtered = [t for t in topics if any(p in t.get("tags", []) for p in preferences)]
        if filtered:
            topics = filtered

    return topics[0] if topics else {
        "name": "utility-tool",
        "type": "tool",
        "desc": "A general purpose utility tool",
        "tags": ["tool", "utility"],
    }


def suggest_projects(count=5):
    topics = research_trending()
    return topics[:count]


def _guess_type(name, desc):
    combined = (name + " " + desc).lower()
    if any(w in combined for w in ["cli", "command", "terminal", "console"]):
        return "cli"
    if any(w in combined for w in ["api", "server", "backend", "rest"]):
        return "api"
    if any(w in combined for w in ["web", "app", "dashboard", "ui"]):
        return "webapp"
    if any(w in combined for w in ["lib", "module", "package", "util"]):
        return "library"
    return "tool"


def _extract_tags(name, desc):
    combined = (name + " " + desc).lower()
    tags = []
    tag_keywords = {
        "cli": ["cli", "command", "terminal"],
        "api": ["api", "server", "rest"],
        "webapp": ["web", "app", "dashboard"],
        "library": ["lib", "module", "package"],
        "tool": ["tool", "utility", "helper"],
        "data": ["data", "csv", "json", "xml"],
        "security": ["security", "auth", "password"],
        "devops": ["devops", "deploy", "docker"],
        "testing": ["test", "lint", "format"],
    }
    for tag, keywords in tag_keywords.items():
        if any(k in combined for k in keywords):
            tags.append(tag)
    return tags or ["utility"]
