# AI Project Builder CLI

Professional CLI tool for AI-powered project generation with full lifecycle management.

## Features

- **Interactive Dashboard** - Rich terminal UI with real-time stats
- **AI Code Generation** - Uses OpenCode Zen free models
- **GitHub Integration** - Auto-create repos, push code, create PRs
- **Project Management** - Create, list, retry, delete projects
- **Model Management** - Test and select AI models
- **Local Database** - SQLite for persistent storage
- **Configurable** - Easy setup with interactive config

## Installation

```bash
cd ai-project-builder-cli
pip install -e .
```

## Quick Start

```bash
# First time setup
apb init

# Or quick setup
apb setup

# Open interactive dashboard
apb dashboard

# Create a project directly
apb create --name my-tool --type cli --desc "My awesome CLI tool"

# Create without AI (uses template)
apb create --name my-lib --type library --desc "A library" --no-ai

# List projects
apb list

# View project details
apb show proj_xxx

# Test a model
apb test big-pickle

# List available models
apb models

# Retry a failed project
apb retry proj_xxx

# Delete a project
apb delete proj_xxx
```

## Commands

| Command | Description |
|---------|-------------|
| `apb init` | Setup wizard for first-time configuration |
| `apb dashboard` | Interactive terminal dashboard |
| `apb create` | Create a new project |
| `apb list` | List all projects |
| `apb show <id>` | Show project details |
| `apb retry <id>` | Retry a failed project |
| `apb delete <id>` | Delete a project |
| `apb test <model>` | Test an AI model |
| `apb models` | List available free models |
| `apb config` | View/update configuration |
| `apb setup` | Quick setup for API keys |

## Configuration

Config is stored at `~/.apb/config.json`:

```json
{
  "github_username": "your-username",
  "github_token": "ghp_xxx",
  "opencode_api_key": "sk-xxx",
  "selected_model": "big-pickle",
  "output_dir": "~/ai-projects"
}
```

## Available Free Models

| Model | ID |
|-------|-----|
| Big Pickle | `big-pickle` |
| DeepSeek V4 Flash Free | `deepseek-v4-flash-free` |
| MiMo-V2.5 Free | `mimo-v2.5-free` |
| North Mini Code Free | `north-mini-code-free` |
| Nemotron 3 Ultra Free | `nemotron-3-ultra-free` |

## Project Structure

```
~/.apb/
├── config.json      # Configuration
├── projects.db      # SQLite database
└── logs/            # Log files

~/ai-projects/       # Generated projects
├── project-1/
├── project-2/
└── ...
```

## Development

```bash
# Install in dev mode
pip install -e .

# Run directly
python -m apb.cli dashboard
```

## License

MIT
