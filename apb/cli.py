import os
import sys
import time
import json
import click
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from rich import box

from .config import (
    load_config, save_config, get_config_value, set_config_value,
    MODELS, PROJECT_TYPES, CONFIG_DIR, DEFAULT_CONFIG,
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

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating project...", total=None)

        project_id = create_project(name, project_type, description)
        progress.update(task, description="Project created in database")

        if use_ai:
            progress.update(task, description="Generating code with AI...")
            code, error = generate_code(name, project_type, description)

            if error:
                progress.update(task, description=f"AI failed: {error}. Using template.")
                code = generate_default_project(name, project_type, description)
            else:
                progress.update(task, description="AI code generated successfully")
        else:
            progress.update(task, description="Using template code...")
            code = generate_default_project(name, project_type, description)

        progress.update(task, description="Saving files to database...")
        for f in code.get("files", []):
            add_file(project_id, f["path"], f["content"])

        add_history(project_id, "generate", "completed", f"Generated {len(code.get('files', []))} files")

        config = load_config()
        output_dir = Path(config.get("output_dir", "~/ai-projects"))
        project_path = output_dir / name

        progress.update(task, description="Writing files to disk...")
        result = init_local_repo(str(project_path), code.get("files", []))

        if result["success"]:
            add_history(project_id, "local", "completed", f"Created at {project_path}")
            update_project(project_id, status="completed")
            progress.update(task, description="Project complete!")
        else:
            add_history(project_id, "local", "failed", result.get("error", "Unknown error"))
            update_project(project_id, status="failed", error_message=result.get("error"))
            progress.update(task, description=f"Failed: {result.get('error')}")

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
            with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
                task = progress.add_task(f"Testing {models[idx]['name']}...", total=None)
                result = test_model(models[idx]["id"])
                progress.update(task, description="Done")

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

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Creating project...", total=None)

        project_id = create_project(name, project_type, desc)

        if no_ai:
            code = generate_default_project(name, project_type, desc)
        else:
            progress.update(task, description="Generating with AI...")
            code, error = generate_code(name, project_type, desc)
            if error:
                progress.update(task, description=f"AI failed: {error}. Using template.")
                code = generate_default_project(name, project_type, desc)

        for f in code.get("files", []):
            add_file(project_id, f["path"], f["content"])

        config = load_config()
        output_dir = Path(config.get("output_dir", "~/ai-projects"))
        project_path = output_dir / name

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


if __name__ == "__main__":
    cli()
