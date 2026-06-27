import os
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".apb"
CONFIG_FILE = CONFIG_DIR / "config.json"
DB_FILE = CONFIG_DIR / "projects.db"
LOGS_DIR = CONFIG_DIR / "logs"

DEFAULT_CONFIG = {
    "github_username": "",
    "github_token": "",
    "opencode_api_key": "",
    "selected_model": "big-pickle",
    "schedule_enabled": False,
    "max_projects_per_day": 3,
    "require_tests": True,
    "auto_merge_to_main": True,
    "auto_retry": True,
    "max_retries": 3,
    "output_dir": str(Path.home() / "ai-projects"),
    "cloudflare_worker_url": "",
}

MODELS = [
    {"id": "big-pickle", "name": "Big Pickle", "free": True},
    {"id": "deepseek-v4-flash-free", "name": "DeepSeek V4 Flash Free", "free": True},
    {"id": "mimo-v2.5-free", "name": "MiMo-V2.5 Free", "free": True},
    {"id": "north-mini-code-free", "name": "North Mini Code Free", "free": True},
    {"id": "nemotron-3-ultra-free", "name": "Nemotron 3 Ultra Free", "free": True},
    {"id": "qwen3.6-plus-free", "name": "Qwen3.6 Plus Free", "free": True},
    {"id": "minimax-m3-free", "name": "MiniMax M3 Free", "free": True},
]

PROJECT_TYPES = [
    {"id": "webapp", "name": "Web Application", "desc": "Full-stack web app with HTML/CSS/JS"},
    {"id": "cli", "name": "CLI Tool", "desc": "Command-line utility"},
    {"id": "library", "name": "Library", "desc": "Reusable npm/Python library"},
    {"id": "api", "name": "API", "desc": "REST/GraphQL API backend"},
    {"id": "tool", "name": "Utility Tool", "desc": "Developer tool or script"},
]


def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    ensure_dirs()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            stored = json.load(f)
            config = {**DEFAULT_CONFIG, **stored}
            return config
    return DEFAULT_CONFIG.copy()


def save_config(config):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_config_value(key):
    config = load_config()
    return config.get(key, DEFAULT_CONFIG.get(key))


def set_config_value(key, value):
    config = load_config()
    config[key] = value
    save_config(config)
