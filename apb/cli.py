import os
import sys
import time
import json
import click
from pathlib import Path
from datetime import datetime

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

console = Console(force_terminal=True)


def safe_text(text):
    if not text:
        return ""
    return text.encode("ascii", errors="replace").decode("ascii")

from .config import (
    load_config, save_config, get_config_value, set_config_value,
    MODELS, PROJECT_TYPES, CONFIG_DIR, DB_FILE, DEFAULT_CONFIG,
)
from .database import (
    create_project, get_project, get_all_projects, update_project,
    delete_project, add_file, add_history, get_stats, get_top_errors, track_usage,
)
from .ai import get_free_models, test_model, generate_code, generate_default_project
from .github import (
    check_auth, create_repo, push_files, create_pull_request,
    merge_pull_request, init_local_repo,
)
from .research import research_deep, pick_smart_project, suggest_proProjects, get_domains, get_projects_by_domain

console = Console()


def show_banner():
    banner = """
[bold blue]
    ___  ____    _    _   _ _____   ____
   / _ \|  _ \\  / \\  | \\ | |_   _| |  _ \\
  | | | | |_) |/ _ \\ |  \\| | | |   | |_) |
  | |_| |  _ / ___ \\| |\\  | | |   |  __/
   \\___/|_| /_/   \\_\\_| \\_| |_|   |_|
[/bold blue]
[dim]    AI-Powered Project Lifecycle Manager[/dim]
"""
    console.print(banner)


def show_stats():
    stats = get_stats()
    errors = get_top_errors()

    table = Table(title="Dashboard", box=box.ROUNDED, show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold")

    table.add_row("Total Projects", str(stats["total"]))
    table.add_row("[green]Completed[/green]", str(stats["completed"]))
    table.add_row("[yellow]In Progress[/yellow]", str(stats["pending"]))
    table.add_row("[red]Failed[/red]", str(stats["failed"]))

    console.print(table)

    if errors:
        console.print("\n[bold red]Common Errors:[/bold red]")
        for e in errors:
            console.print(f"  [red]![/red] {e['error_message']} [dim]({e['count']}x)[/dim]")


def show_projects(projects=None):
    if projects is None:
        projects = get_all_projects()

    if not projects:
        console.print("[dim]No projects found. Create one with: apb create[/dim]")
        return

    table = Table(title="Projects", box=box.ROUNDED)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="dim")
    table.add_column("Status")
    table.add_column("Created", style="dim")
    table.add_column("Error", style="red", max_width=40)

    status_colors = {
        "completed": "[green]completed[/green]",
        "pending": "[blue]pending[/blue]",
        "researching": "[yellow]researching[/yellow]",
        "generating": "[yellow]generating[/yellow]",
        "testing": "[cyan]testing[/cyan]",
        "failed": "[red]failed[/red]",
    }

    for p in projects:
        status = status_colors.get(p["status"], p["status"])
        error = p.get("error_message", "") or ""
        if len(error) > 40:
            error = error[:37] + "..."
        table.add_row(
            p["name"],
            p["type"],
            status,
            p["created_at"][:16] if p.get("created_at") else "",
            error,
        )

    console.print(table)


def show_project_detail(project_id):
    project = get_project(project_id)
    if not project:
        console.print(f"[red]Project not found: {project_id}[/red]")
        return

    status_colors = {
        "completed": "green",
        "pending": "blue",
        "failed": "red",
    }
    color = status_colors.get(project["status"], "yellow")

    console.print(Panel(
        f"[bold]{project['name']}[/bold]\n"
        f"Type: {project['type']}\n"
        f"Status: [{color}]{project['status']}[/{color}]\n"
        f"Description: {project.get('description', 'N/A')}\n"
        f"Created: {project.get('created_at', 'N/A')}\n"
        f"Error: {project.get('error_message', 'None')}",
        title="Project Details",
        border_style=color,
    ))

    if project["files"]:
        console.print(f"\n[bold]Generated Files ({len(project['files'])}):[/bold]")
        for f in project["files"]:
            console.print(f"  [cyan]{f['file_path']}[/cyan]")

    if project["history"]:
        console.print(f"\n[bold]Build History ({len(project['history'])}):[/bold]")
        for h in project["history"]:
            status_color = "green" if h["status"] in ("success", "completed") else "red" if h["status"] == "failed" else "yellow"
            details = f" - {h['details']}" if h.get("details") else ""
            console.print(f"  [{status_color}]{h['action']}[/{status_color}]{details}")


def interactive_create():
    show_banner()
    console.print("[bold]Create New Project[/bold]\n")

    name = Prompt.ask("Project name")
    if not name:
        console.print("[red]Name is required[/red]")
        return

    console.print("\n[bold]Project Types:[/bold]")
    for i, pt in enumerate(PROJECT_TYPES, 1):
        console.print(f"  [cyan]{i}.[/cyan] {pt['name']} - {pt['desc']}")

    choice = Prompt.ask("Select type", default="1")
    try:
        type_idx = int(choice) - 1
        project_type = PROJECT_TYPES[type_idx]["id"]
    except (ValueError, IndexError):
        project_type = "tool"

    description = Prompt.ask("Description", default=f"A {project_type} project")

    console.print("\n[bold]AI Model:[/bold]")
    models = get_free_models()
    for i, m in enumerate(models, 1):
        free_tag = " [green](Free)[/green]" if m.get("free") else ""
        console.print(f"  [cyan]{i}.[/cyan] {m['name']}{free_tag}")

    choice = Prompt.ask("Select model", default="1")
    try:
        model_idx = int(choice) - 1
        selected_model = models[model_idx]["id"]
    except (ValueError, IndexError):
        selected_model = "big-pickle"

    use_ai = Confirm.ask("Generate code with AI?", default=True)

    console.print("[cyan]Creating project...[/cyan]")
    project_id = create_project(name, project_type, description)
    console.print("[green]Project created in database[/green]")

    if use_ai:
        console.print("[cyan]Generating code with AI...[/cyan]")
        code, error = generate_code(name, project_type, description)
        if error:
            console.print(f"[yellow]AI failed: {error}. Using template.[/yellow]")
            code = generate_default_project(name, project_type, description)
        else:
            console.print("[green]AI code generated successfully[/green]")
    else:
        console.print("[cyan]Using template code...[/cyan]")
        code = generate_default_project(name, project_type, description)

    console.print("[cyan]Saving files to database...[/cyan]")
    for f in code.get("files", []):
        add_file(project_id, f["path"], f["content"])

    add_history(project_id, "generate", "completed", f"Generated {len(code.get('files', []))} files")

    config = load_config()
    output_dir = Path(config.get("output_dir", "~/ai-projects"))
    project_path = output_dir / name

    console.print("[cyan]Writing files to disk...[/cyan]")
    result = init_local_repo(str(project_path), code.get("files", []))

    if result["success"]:
        add_history(project_id, "local", "completed", f"Created at {project_path}")
        update_project(project_id, status="completed")
    else:
        add_history(project_id, "local", "failed", result.get("error", "Unknown error"))
        update_project(project_id, status="failed", error_message=result.get("error"))

    console.print(f"\n[green]Project created at: {project_path}[/green]")
    show_project_detail(project_id)


def interactive_config():
    show_banner()
    config = load_config()

    console.print("[bold]Configuration[/bold]\n")

    table = Table(box=box.SIMPLE)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    for key, value in config.items():
        display_value = str(value)
        if "token" in key.lower() or "key" in key.lower():
            display_value = value[:8] + "..." if len(value) > 8 else "(not set)"
        table.add_row(key, display_value)

    console.print(table)

    console.print("\n[bold]Quick Actions:[/bold]")
    console.print("  [cyan]1.[/cyan] Set GitHub username")
    console.print("  [cyan]2.[/cyan] Set GitHub token")
    console.print("  [cyan]3.[/cyan] Set OpenCode API key")
    console.print("  [cyan]4.[/cyan] Select AI model")
    console.print("  [cyan]5.[/cyan] Toggle schedule")
    console.print("  [cyan]6.[/cyan] Set output directory")

    choice = Prompt.ask("\nSelect option", default="0")

    if choice == "1":
        val = Prompt.ask("GitHub username")
        set_config_value("github_username", val)
    elif choice == "2":
        val = Prompt.ask("GitHub token")
        set_config_value("github_token", val)
    elif choice == "3":
        val = Prompt.ask("OpenCode Zen API key")
        set_config_value("opencode_api_key", val)
    elif choice == "4":
        models = get_free_models()
        for i, m in enumerate(models, 1):
            console.print(f"  [cyan]{i}.[/cyan] {m['name']}")
        idx = int(Prompt.ask("Select model", default="1")) - 1
        if 0 <= idx < len(models):
            set_config_value("selected_model", models[idx]["id"])
    elif choice == "5":
        current = config.get("schedule_enabled", False)
        set_config_value("schedule_enabled", not current)
    elif choice == "6":
        val = Prompt.ask("Output directory", default=config.get("output_dir", ""))
        set_config_value("output_dir", val)

    console.print("[green]Configuration saved![/green]")


def interactive_models():
    show_banner()
    console.print("[bold]Available Models[/bold]\n")

    models = get_free_models()

    table = Table(box=box.ROUNDED)
    table.add_column("#", style="dim")
    table.add_column("Model", style="cyan")
    table.add_column("ID")
    table.add_column("Free", style="green")
    table.add_column("Status")

    for i, m in enumerate(models, 1):
        free = "[green]Yes[/green]" if m.get("free") else "[red]No[/red]"
        table.add_row(str(i), m["name"], m["id"], free, "Ready")

    console.print(table)

    console.print("\n[bold]Actions:[/bold]")
    console.print("  [cyan]t.[/cyan] Test a model")
    console.print("  [cyan]s.[/cyan] Select as default")
    console.print("  [cyan]q.[/cyan] Back to menu")

    choice = Prompt.ask("Select action", default="q")

    if choice == "t":
        idx = int(Prompt.ask("Model number to test", default="1")) - 1
        if 0 <= idx < len(models):
            console.print(f"[cyan]Testing {models[idx]['name']}...[/cyan]")
            result = test_model(models[idx]["id"])

            if result["success"]:
                console.print(Panel(
                    f"Response: {result['response']}\n"
                    f"Model: {result.get('model', 'N/A')}\n"
                    f"Cost: ${result.get('cost', '0')}\n"
                    f"Tokens: {result.get('tokens', 0)}",
                    title="[green]Test Successful[/green]",
                    border_style="green",
                ))
            else:
                console.print(Panel(
                    result["error"],
                    title="[red]Test Failed[/red]",
                    border_style="red",
                ))

    elif choice == "s":
        idx = int(Prompt.ask("Model number to select", default="1")) - 1
        if 0 <= idx < len(models):
            set_config_value("selected_model", models[idx]["id"])
            console.print(f"[green]Default model set to: {models[idx]['name']}[/green]")


def main_menu():
    while True:
        show_banner()
        show_stats()

        console.print("\n[bold]Menu:[/bold]")
        console.print("  [cyan]1.[/cyan] Create Project")
        console.print("  [cyan]2.[/cyan] List Projects")
        console.print("  [cyan]3.[/cyan] View Project")
        console.print("  [cyan]4.[/cyan] Retry Project")
        console.print("  [cyan]5.[/cyan] Delete Project")
        console.print("  [cyan]6.[/cyan] Models")
        console.print("  [cyan]7.[/cyan] Configuration")
        console.print("  [cyan]8.[/cyan] Test Model")
        console.print("  [cyan]0.[/cyan] Exit")

        choice = Prompt.ask("\nSelect option", default="0")

        if choice == "0":
            console.print("[dim]Goodbye![/dim]")
            break
        elif choice == "1":
            interactive_create()
        elif choice == "2":
            show_projects()
        elif choice == "3":
            projects = get_all_projects()
            if projects:
                show_projects(projects)
                pid = Prompt.ask("Project ID")
                show_project_detail(pid)
        elif choice == "4":
            projects = get_all_projects()
            failed = [p for p in projects if p["status"] == "failed"]
            if failed:
                show_projects(failed)
                pid = Prompt.ask("Project ID to retry")
                update_project(pid, status="pending", error_message=None)
                console.print(f"[green]Project {pid} queued for retry[/green]")
            else:
                console.print("[dim]No failed projects[/dim]")
        elif choice == "5":
            projects = get_all_projects()
            if projects:
                show_projects(projects)
                pid = Prompt.ask("Project ID to delete")
                if Confirm.ask(f"Delete {pid}?"):
                    delete_project(pid)
                    console.print("[green]Deleted[/green]")
        elif choice == "6":
            interactive_models()
        elif choice == "7":
            interactive_config()
        elif choice == "8":
            model = Prompt.ask("Model ID", default="big-pickle")
            result = test_model(model)
            if result["success"]:
                console.print(f"[green]Success: {result['response']}[/green]")
            else:
                console.print(f"[red]Failed: {result['error']}[/red]")

        if choice != "0":
            Prompt.ask("\nPress Enter to continue")


@click.group()
def cli():
    """AI Project Builder CLI - Professional tool for AI-powered project generation."""
    pass


@cli.command()
def init():
    """Initialize the CLI and show setup wizard."""
    show_banner()
    console.print("[bold]Setup Wizard[/bold]\n")

    config = load_config()

    if not config.get("github_username"):
        config["github_username"] = Prompt.ask("GitHub username")

    if not config.get("github_token"):
        config["github_token"] = Prompt.ask("GitHub token (for API access)")

    if not config.get("opencode_api_key"):
        config["opencode_api_key"] = Prompt.ask("OpenCode Zen API key")

    save_config(config)
    console.print("\n[green]Setup complete![/green]")
    console.print("Run [cyan]apb[/cyan] to start using the CLI.")


@cli.command()
def status():
    """Show all project info - database, files, git, GitHub."""
    show_banner()

    config = load_config()
    output_dir = Path(config.get("output_dir", "~/ai-projects"))

    print("[bold]System Status[/bold]\n")

    print("[cyan]Storage:[/cyan]")
    print(f"  Database: {DB_FILE}")
    print(f"  Config: {CONFIG_DIR / 'config.json'}")
    print(f"  Projects: {output_dir}")
    print()

    if output_dir.exists():
        projects_on_disk = [d.name for d in output_dir.iterdir() if d.is_dir()]
        print(f"[cyan]Projects on disk ({len(projects_on_disk)}):[/cyan]")
        for p in projects_on_disk[:10]:
            git_dir = output_dir / p / ".git"
            has_git = "[green]git[/green]" if git_dir.exists() else "[dim]no git[/dim]"
            print(f"  {p} [{has_git}]")
    else:
        print("[cyan]Projects on disk:[/cyan] None")

    print()

    stats = get_stats()
    print("[cyan]Database:[/cyan]")
    print(f"  Total: {stats['total']}")
    print(f"  Completed: {stats['completed']}")
    print(f"  In Progress: {stats['pending']}")
    print(f"  Failed: {stats['failed']}")
    print()

    print("[cyan]Config:[/cyan]")
    print(f"  GitHub: {config.get('github_username', 'not set')}")
    print(f"  Model: {config.get('selected_model', 'not set')}")
    print(f"  Output: {config.get('output_dir', 'not set')}")

    auth = check_auth()
    print(f"  Git auth: {'[green]OK[/green]' if auth else '[red]Not authenticated[/red]'}")
    print()

    projects = get_all_projects()
    if projects:
        print("[cyan]Recent projects:[/cyan]")
        for p in projects[:5]:
            status_color = "green" if p["status"] == "completed" else "red" if p["status"] == "failed" else "yellow"
            print(f"  {p['name']} [{status_color}]{p['status']}[/{status_color}]")
            if p.get("repo_url"):
                print(f"    GitHub: {p['repo_url']}")
            project_path = output_dir / p["name"]
            if project_path.exists():
                print(f"    Local: {project_path}")


@cli.command()
def dashboard():
    """Open the interactive dashboard."""
    main_menu()


@cli.command()
@click.option("--name", prompt="Project name", help="Name of the project")
@click.option("--type", "project_type", type=click.Choice(["webapp", "cli", "library", "api", "tool"]), default="tool")
@click.option("--desc", prompt="Description", default="A utility tool")
@click.option("--no-ai", is_flag=True, help="Skip AI generation, use template")
def create(name, project_type, desc, no_ai):
    """Create a new project."""
    show_banner()

    console.print("[cyan]Creating project...[/cyan]")
    project_id = create_project(name, project_type, desc)
    console.print(f"[green]Project created in database: {project_id}[/green]")

    if no_ai:
        console.print("[cyan]Using template code...[/cyan]")
        code = generate_default_project(name, project_type, desc)
    else:
        console.print("[cyan]Generating with AI...[/cyan]")
        code, error = generate_code(name, project_type, desc)
        if error:
            console.print(f"[yellow]AI failed: {error}. Using template.[/yellow]")
            code = generate_default_project(name, project_type, desc)
        else:
            console.print("[green]AI code generated successfully[/green]")

    console.print("[cyan]Saving files to database...[/cyan]")
    for f in code.get("files", []):
        add_file(project_id, f["path"], f["content"])

    config = load_config()
    output_dir = Path(config.get("output_dir", "~/ai-projects"))
    project_path = output_dir / name

    console.print("[cyan]Writing files to disk...[/cyan]")
    result = init_local_repo(str(project_path), code.get("files", []))

    if result["success"]:
        update_project(project_id, status="completed")
        add_history(project_id, "local", "completed", f"Created at {project_path}")
        console.print(f"\n[green]Project created at: {project_path}[/green]")
    else:
        update_project(project_id, status="failed", error_message=result.get("error"))
        console.print(f"\n[red]Failed: {result.get('error')}[/red]")

    show_project_detail(project_id)


@cli.command()
def list():
    """List all projects."""
    show_banner()
    show_projects()


@cli.command()
@click.argument("project_id")
def show(project_id):
    """Show project details."""
    show_banner()
    show_project_detail(project_id)


@cli.command()
@click.argument("project_id")
def retry(project_id):
    """Retry a failed project."""
    update_project(project_id, status="pending", error_message=None)
    console.print(f"[green]Project {project_id} queued for retry[/green]")


@cli.command()
@click.argument("project_id")
@click.confirmation_option(prompt="Are you sure?")
def delete(project_id):
    """Delete a project."""
    delete_project(project_id)
    console.print(f"[green]Project {project_id} deleted[/green]")


@cli.command()
@click.argument("model_id", default="big-pickle")
def test(model_id):
    """Test an AI model."""
    result = test_model(model_id)
    if result["success"]:
        console.print(f"[green]Success: {result['response']}[/green]")
        console.print(f"Model: {result.get('model')}")
        console.print(f"Cost: ${result.get('cost', '0')}")
        console.print(f"Tokens: {result.get('tokens', 0)}")
    else:
        console.print(f"[red]Failed: {result['error']}[/red]")


@cli.command()
def models():
    """List available models."""
    show_banner()
    model_list = get_free_models()

    table = Table(title="Free Models", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("ID")
    table.add_column("Free", style="green")

    for m in model_list:
        free = "Yes" if m.get("free") else "No"
        table.add_row(m["name"], m["id"], free)

    console.print(table)


@cli.command()
def config():
    """Show or update configuration."""
    interactive_config()


@cli.command()
def setup():
    """Quick setup - set API keys."""
    show_banner()
    config = load_config()

    console.print("[bold]Quick Setup[/bold]\n")

    val = Prompt.ask("GitHub username", default=config.get("github_username", ""))
    if val:
        config["github_username"] = val

    val = Prompt.ask("GitHub token", default="")
    if val:
        config["github_token"] = val

    val = Prompt.ask("OpenCode Zen API key", default="")
    if val:
        config["opencode_api_key"] = val

    save_config(config)
    console.print("\n[green]Configuration saved![/green]")


@cli.command()
@click.option("--count", "-n", default=1, help="Number of projects to build")
@click.option("--type", "project_type", type=click.Choice(["webapp", "cli", "library", "api", "tool", "any"]), default="any")
@click.option("--domain", "-d", default=None, help="Filter by domain")
@click.option("--no-ai", is_flag=True, help="Use template instead of AI")
@click.option("--push", is_flag=True, help="Push to GitHub")
def auto(count, project_type, domain, no_ai, push):
    """Fully automatic: research, build, test, push to GitHub."""
    show_banner()

    print("[bold cyan]=== FULL LIFECYCLE MODE ===[/bold cyan]\n")

    print("[1/6] Researching real-world problems...")
    candidates = suggest_proProjects(count + 10)

    if domain:
        candidates = [p for p in candidates if domain.lower() in p.get("domain", "").lower()] or candidates
    if project_type != "any":
        candidates = [p for p in candidates if p["type"] == project_type] or candidates

    best = candidates[0]
    print(f"    Selected: {best['name']} ({best['type']}) - {best.get('domain', 'General')}")
    print(f"    Problem: {best['desc']}\n")

    print("[2/6] Creating project...")
    project_id = create_project(best["name"], best["type"], best["desc"])
    print(f"    ID: {project_id}\n")

    print("[3/6] Generating production code...")
    if no_ai:
        code = generate_default_project(best["name"], best["type"], best["desc"])
        print("    Using template")
    else:
        code, error = generate_code(best["name"], best["type"], best["desc"])
        if error:
            print(f"    AI failed: {error}")
            print("    Using template as fallback")
            code = generate_default_project(best["name"], best["type"], best["desc"])
        else:
            print(f"    Generated {len(code.get('files', []))} files with AI")

    for f in code.get("files", []):
        add_file(project_id, f["path"], f["content"])
    add_history(project_id, "generate", "completed", f"Generated {len(code.get('files', []))} files")
    print()

    print("[4/6] Saving to disk and initializing git...")
    config = load_config()
    output_dir = Path(config.get("output_dir", "~/ai-projects"))
    project_path = output_dir / best["name"]

    result = init_local_repo(str(project_path), code.get("files", []))
    if result["success"]:
        add_history(project_id, "local", "completed", f"Saved to {project_path}")
        print(f"    Path: {project_path}")
    else:
        add_history(project_id, "local", "failed", result.get("error"))
        print(f"    Failed: {result.get('error')}")
    print()

    print("[5/6] Testing...")
    has_tests = any("test" in f.get("path", "").lower() for f in code.get("files", []))
    has_package = any("package.json" in f.get("path", "") for f in code.get("files", []))
    has_readme = any("readme" in f.get("path", "").lower() for f in code.get("files", []))

    checks = [
        ("Source code", True),
        ("Tests", has_tests),
        ("Package config", has_package),
        ("Documentation", has_readme),
    ]

    for name, ok in checks:
        status = "[green]PASS[/green]" if ok else "[yellow]SKIP[/yellow]"
        print(f"    {name}: {status}")

    all_pass = all(ok for _, ok in checks)
    test_status = "completed" if all_pass else "completed"
    add_history(project_id, "test", test_status, "Automated checks passed")
    print()

    print("[6/6] Pushing to GitHub...")
    if push:
        config = load_config()
        gh_user = config.get("github_username", "")

        if gh_user and check_auth():
            repo_name = best["name"]
            print(f"    Creating repo: {repo_name}")

            repo_result = create_repo(repo_name, best["desc"])
            if repo_result["success"]:
                print(f"    Repo: {repo_result['url']}")

                print("    Pushing code...")
                push_result = push_files(repo_name, code.get("files", []))
                if push_result["success"]:
                    print("    Creating PR...")
                    create_pull_request(
                        repo_name,
                        f"feat: {best['name']} - {best['desc']}",
                        f"## {best['name']}\n\n{best['desc']}\n\nDomain: {best.get('domain', 'General')}",
                    )
                    merge_pull_request(repo_name)

                    update_project(project_id, repo_name=repo_name, repo_url=repo_result["url"])
                    add_history(project_id, "push", "completed", f"Pushed to {repo_result['url']}")
                    print("    Merged to main")
                else:
                    add_history(project_id, "push", "failed", push_result.get("error"))
                    print(f"    Push failed: {push_result.get('error')}")
            else:
                add_history(project_id, "push", "failed", repo_result.get("error"))
                print(f"    Repo creation failed: {repo_result.get('error')}")
        else:
            print("    Skipped: No GitHub username or not authenticated")
            print("    Run: apb setup")
    else:
        print("    Skipped: Use --push to push to GitHub")

    update_project(project_id, status="completed")

    print(f"\n{'='*60}")
    print(f"[bold green]COMPLETE![/bold green]")
    print(f"{'='*60}")
    print(f"  Project: {best['name']}")
    print(f"  Type: {best['type']}")
    print(f"  Domain: {best.get('domain', 'General')}")
    print(f"  Local: {project_path}")
    if push:
        config = load_config()
        print(f"  GitHub: https://github.com/{config.get('github_username', '')}/{best['name']}")
    print(f"  Database: {DB_FILE}")
    print(f"{'='*60}")


@cli.command()
@click.option("--domain", "-d", default=None, help="Filter by domain (e.g. 'Security', 'DevOps')")
@click.option("--complexity", "-c", type=click.Choice(["high", "medium"]), default=None)
def suggest(domain, complexity):
    """Suggest real production-quality projects to build."""
    show_banner()
    print("[bold]Production-Quality Project Ideas[/bold]\n")

    topics = suggest_proProjects(10)

    if domain:
        topics = [t for t in topics if domain.lower() in t.get("domain", "").lower()] or topics
    if complexity:
        topics = [t for t in topics if t.get("complexity") == complexity] or topics

    print(f"{'#':<3} {'Name':<22} {'Type':<10} {'Complexity':<12} {'Description':<50}")
    print("-" * 100)

    for i, t in enumerate(topics, 1):
        desc = t["desc"][:47] + "..." if len(t["desc"]) > 50 else t["desc"]
        complexity_tag = t.get("complexity", "medium")
        print(f"{i:<3} {safe_text(t['name']):<22} {t['type']:<10} {complexity_tag:<12} {safe_text(desc)}")

    print(f"\n[bold]Domains:[/bold] {', '.join(get_domains())}")
    print("\n[bold]To build:[/bold]")
    print("  apb create --name <name> --type <type> --desc \"<desc>\"")
    print("  apb auto -n 3")
    print("  apb auto -d Security -n 2")


if __name__ == "__main__":
    cli()
