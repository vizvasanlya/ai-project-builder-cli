import os
import subprocess
import requests
from pathlib import Path
from .config import load_config


def get_headers():
    config = load_config()
    token = config.get("github_token", "")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }


def get_username():
    config = load_config()
    return config.get("github_username", "")


def check_auth():
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def create_repo(name, description=""):
    username = get_username()
    headers = get_headers()

    resp = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json={
            "name": name,
            "description": description,
            "auto_init": False,
            "private": False,
        },
        timeout=30,
    )

    if resp.status_code == 201:
        return {"success": True, "url": resp.json()["html_url"], "name": name}
    elif resp.status_code == 422:
        return {"success": True, "url": f"https://github.com/{username}/{name}", "name": name, "exists": True}
    else:
        try:
            error = resp.json()
            return {"success": False, "error": error.get("message", "Unknown error")}
        except Exception:
            return {"success": False, "error": f"HTTP {resp.status_code}"}


def push_files(repo_name, files, branch="develop"):
    username = get_username()
    headers = get_headers()
    repo_full = f"{username}/{repo_name}"

    main_ref = requests.get(
        f"https://api.github.com/repos/{repo_full}/git/ref/heads/main",
        headers=headers,
        timeout=30,
    )

    if main_ref.ok:
        main_sha = main_ref.json()["object"]["sha"]
        requests.post(
            f"https://api.github.com/repos/{repo_full}/git/refs",
            headers=headers,
            json={"ref": f"refs/heads/{branch}", "sha": main_sha},
            timeout=30,
        )

    for file in files:
        import base64
        content = base64.b64encode(file["content"].encode()).decode()

        existing = requests.get(
            f"https://api.github.com/repos/{repo_full}/contents/{file['path']}?ref={branch}",
            headers=headers,
            timeout=30,
        )

        body = {"message": f"Add {file['path']}", "content": content, "branch": branch}
        if existing.ok:
            body["sha"] = existing.json()["sha"]

        requests.put(
            f"https://api.github.com/repos/{repo_full}/contents/{file['path']}",
            headers=headers,
            json=body,
            timeout=30,
        )

    return {"success": True}


def create_pull_request(repo_name, title, body="", branch="develop"):
    username = get_username()
    headers = get_headers()
    repo_full = f"{username}/{repo_name}"

    resp = requests.post(
        f"https://api.github.com/repos/{repo_full}/pulls",
        headers=headers,
        json={"title": title, "body": body, "head": branch, "base": "main"},
        timeout=30,
    )

    if resp.ok:
        return {"success": True, "url": resp.json()["html_url"]}
    else:
        return {"success": False, "error": "Failed to create PR"}


def merge_pull_request(repo_name):
    username = get_username()
    headers = get_headers()
    repo_full = f"{username}/{repo_name}"

    pulls = requests.get(
        f"https://api.github.com/repos/{repo_full}/pulls?state=open",
        headers=headers,
        timeout=30,
    )

    if pulls.ok and pulls.json():
        pr_number = pulls.json()[0]["number"]
        resp = requests.put(
            f"https://api.github.com/repos/{repo_full}/pulls/{pr_number}/merge",
            headers=headers,
            json={"merge_method": "squash"},
            timeout=30,
        )
        return {"success": resp.ok}

    return {"success": False, "error": "No open PRs found"}


def init_local_repo(project_path, files):
    project_path = Path(project_path)
    project_path.mkdir(parents=True, exist_ok=True)

    for file in files:
        file_path = project_path / file["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file["content"])

    try:
        subprocess.run(["git", "init"], cwd=str(project_path), capture_output=True, timeout=10)
        subprocess.run(["git", "add", "."], cwd=str(project_path), capture_output=True, timeout=10)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=str(project_path),
            capture_output=True,
            timeout=10,
        )
        return {"success": True, "path": str(project_path)}
    except Exception as e:
        return {"success": False, "error": str(e)}
