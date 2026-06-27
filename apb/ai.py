import json
import requests
from .config import load_config, MODELS


API_BASE = "https://opencode.ai/zen/v1"


def get_free_models():
    try:
        resp = requests.get(f"{API_BASE}/models", timeout=10)
        if resp.ok:
            data = resp.json()
            all_models = data.get("data", [])
            free = []
            for m in all_models:
                mid = m.get("id", "")
                if "-free" in mid or mid == "big-pickle":
                    free.append({
                        "id": mid,
                        "name": format_model_name(mid),
                        "provider": m.get("owned_by", "opencode"),
                        "free": True,
                    })
            return free
    except Exception:
        pass
    return [{"id": m["id"], "name": m["name"], "free": True} for m in MODELS]


def format_model_name(model_id):
    names = {
        "big-pickle": "Big Pickle",
        "deepseek-v4-flash-free": "DeepSeek V4 Flash Free",
        "mimo-v2.5-free": "MiMo-V2.5 Free",
        "north-mini-code-free": "North Mini Code Free",
        "nemotron-3-ultra-free": "Nemotron 3 Ultra Free",
        "qwen3.6-plus-free": "Qwen3.6 Plus Free",
        "minimax-m3-free": "MiniMax M3 Free",
    }
    if model_id in names:
        return names[model_id]
    return model_id.replace("-", " ").title()


def test_model(model_id):
    config = load_config()
    api_key = config.get("opencode_api_key", "")
    if not api_key:
        return {"success": False, "error": "No API key configured. Run: apb config set opencode_api_key YOUR_KEY"}

    try:
        resp = requests.post(
            f"{API_BASE}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 20,
            },
            timeout=30,
        )

        if resp.status_code == 429:
            return {"success": False, "error": "Rate limited. Free APIs often block server/cloud IPs. Try from your local machine."}

        if not resp.ok:
            try:
                err = resp.json()
                return {"success": False, "error": err.get("error", {}).get("message", resp.text[:200])}
            except Exception:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        data = resp.json()
        content = ""
        if data.get("choices"):
            content = data["choices"][0].get("message", {}).get("content", "")
        return {
            "success": True,
            "response": content or "(empty)",
            "model": data.get("model"),
            "cost": data.get("cost", "0"),
            "tokens": data.get("usage", {}).get("total_tokens", 0),
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_code(project_name, project_type, description):
    config = load_config()
    api_key = config.get("opencode_api_key", "")
    model = config.get("selected_model", "big-pickle")

    if not api_key:
        return None, "No API key configured"

    prompt = f"""Generate a production-ready {project_type} called "{project_name}".

Description: {description}

Requirements:
- Clean, readable code
- Proper error handling
- TypeScript support via JSDoc
- Unit tests
- Documentation

Return the code as a JSON object with this structure:
{{
  "name": "project-name",
  "description": "Brief description",
  "files": [
    {{"path": "src/index.js", "content": "file content"}},
    {{"path": "package.json", "content": "{{...}}"}},
    {{"path": "README.md", "content": "# Project..."}},
    {{"path": "tests/index.test.js", "content": "test code"}}
  ]
}}

Make sure all code is syntactically valid."""

    try:
        resp = requests.post(
            f"{API_BASE}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 4000,
            },
            timeout=120,
        )

        if resp.status_code == 429:
            return None, "Rate limited by provider"

        if not resp.ok:
            try:
                err = resp.json()
                return None, err.get("error", {}).get("message", "API error")
            except Exception:
                return None, f"HTTP {resp.status_code}"

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)

        json_match = content[content.find("{"):content.rfind("}") + 1]
        parsed = json.loads(json_match)

        if "files" not in parsed:
            return None, "Invalid response: no files array"

        return parsed, None

    except json.JSONDecodeError:
        return None, "Failed to parse AI response as JSON"
    except requests.exceptions.Timeout:
        return None, "Request timed out"
    except Exception as e:
        return None, str(e)


def generate_default_project(project_name, project_type, description):
    index_content = f"""/**
 * {project_name}
 * {description}
 */

export function main() {{
  console.log("Hello from {project_name}");
}}

export default main;"""

    readme_content = f"""# {project_name}

{description}

## Installation

```bash
npm install {project_name}
```

## Usage

```javascript
import {{ main }} from "{project_name}";

main();
```

## License

MIT"""

    test_content = f"""import {{ describe, it }} from 'node:test';
import assert from 'node:assert';
import {{ main }} from '../src/index.js';

describe('{project_name}', () => {{
  it('should export main function', () => {{
    assert(typeof main === 'function');
  }});
}});"""

    package_json = json.dumps({
        "name": project_name,
        "version": "1.0.0",
        "description": description,
        "main": "src/index.js",
        "type": "module",
        "scripts": {
            "test": "node --test tests/",
            "start": "node src/index.js",
        },
        "keywords": [project_type],
        "license": "MIT",
    }, indent=2)

    return {
        "name": project_name,
        "description": description,
        "files": [
            {"path": "src/index.js", "content": index_content},
            {"path": "package.json", "content": package_json},
            {"path": "README.md", "content": readme_content},
            {"path": "tests/index.test.js", "content": test_content},
        ],
    }
