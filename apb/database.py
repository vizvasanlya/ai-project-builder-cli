import sqlite3
import json
from datetime import datetime
from pathlib import Path
from .config import DB_FILE, ensure_dirs


def get_db():
    ensure_dirs()
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            description TEXT,
            repo_name TEXT,
            repo_url TEXT,
            branch TEXT DEFAULT 'develop',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3
        );

        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            content TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS build_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            request_count INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def create_project(name, project_type, description=""):
    project_id = f"proj_{int(datetime.now().timestamp() * 1000)}_{name}"
    conn = get_db()
    conn.execute(
        "INSERT INTO projects (id, name, type, status, description) VALUES (?, ?, ?, 'pending', ?)",
        (project_id, name, project_type, description),
    )
    conn.execute(
        "INSERT INTO build_history (project_id, action, status, details) VALUES (?, 'created', 'success', ?)",
        (project_id, f"Created: {description}"),
    )
    conn.commit()
    conn.close()
    return project_id


def get_project(project_id):
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project:
        files = conn.execute(
            "SELECT * FROM project_files WHERE project_id = ? ORDER BY file_path",
            (project_id,),
        ).fetchall()
        history = conn.execute(
            "SELECT * FROM build_history WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        conn.close()
        return {
            **dict(project),
            "files": [dict(f) for f in files],
            "history": [dict(h) for h in history],
        }
    conn.close()
    return None


def get_all_projects():
    conn = get_db()
    projects = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(p) for p in projects]


def update_project(project_id, **kwargs):
    conn = get_db()
    sets = []
    values = []
    for key, value in kwargs.items():
        if key in ("status", "error_message", "repo_name", "repo_url", "branch", "retry_count"):
            sets.append(f"{key} = ?")
            values.append(value)
    if sets:
        sets.append("updated_at = CURRENT_TIMESTAMP")
        values.append(project_id)
        conn.execute(f"UPDATE projects SET {', '.join(sets)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def delete_project(project_id):
    conn = get_db()
    conn.execute("DELETE FROM project_files WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM build_history WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


def add_file(project_id, file_path, content):
    conn = get_db()
    conn.execute(
        "INSERT INTO project_files (project_id, file_path, content) VALUES (?, ?, ?)",
        (project_id, file_path, content),
    )
    conn.commit()
    conn.close()


def add_history(project_id, action, status, details=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO build_history (project_id, action, status, details) VALUES (?, ?, ?, ?)",
        (project_id, action, status, details),
    )
    conn.commit()
    conn.close()


def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'completed'").fetchone()[0]
    failed = conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'failed'").fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE status IN ('pending', 'researching', 'generating', 'testing')"
    ).fetchone()[0]
    conn.close()
    return {"total": total, "completed": completed, "failed": failed, "pending": pending}


def get_top_errors(limit=5):
    conn = get_db()
    errors = conn.execute(
        "SELECT error_message, COUNT(*) as count FROM projects WHERE status = 'failed' AND error_message IS NOT NULL GROUP BY error_message ORDER BY count DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(e) for e in errors]


def track_usage(model, tokens):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM api_usage WHERE model = ? AND date = ?", (model, today)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE api_usage SET tokens_used = tokens_used + ?, request_count = request_count + 1 WHERE id = ?",
            (tokens, existing[0]),
        )
    else:
        conn.execute(
            "INSERT INTO api_usage (model, tokens_used, request_count, date) VALUES (?, ?, 1, ?)",
            (model, tokens, today),
        )
    conn.commit()
    conn.close()


init_db()
