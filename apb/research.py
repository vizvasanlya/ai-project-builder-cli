import requests
import random
import json
from datetime import datetime, timedelta


PROBLEM_DOMAINS = [
    {
        "domain": "Developer Productivity",
        "problems": [
            {"name": "pr-comment-bot", "type": "tool", "desc": "GitHub PR bot that suggests code improvements using AST analysis", "complexity": "high"},
            {"name": "dep-audit", "type": "cli", "desc": "Audit npm/pip dependencies for vulnerabilities, outdated versions, and license conflicts", "complexity": "high"},
            {"name": "git-blame-analyzer", "type": "tool", "desc": "Analyze git blame data to find code hotspots and technical debt", "complexity": "medium"},
            {"name": "ci-cost-calculator", "type": "tool", "desc": "Calculate CI/CD pipeline costs across GitHub Actions, CircleCI, and Travis", "complexity": "medium"},
            {"name": "env-diff", "type": "cli", "desc": "Compare environment variables across dev/staging/prod and find drift", "complexity": "medium"},
            {"name": "api-doc-generator", "type": "tool", "desc": "Generate OpenAPI docs from existing REST endpoints by analyzing traffic", "complexity": "high"},
        ]
    },
    {
        "domain": "Data Engineering",
        "problems": [
            {"name": "csv-merger", "type": "tool", "desc": "Merge multiple CSV files with schema detection, type inference, and conflict resolution", "complexity": "medium"},
            {"name": "json-stream-processor", "type": "library", "desc": "Stream process large JSON files without loading into memory", "complexity": "high"},
            {"name": "db-migration-tool", "type": "cli", "desc": "Generate database migration scripts by comparing schema snapshots", "complexity": "high"},
            {"name": "log-correlator", "type": "tool", "desc": "Correlate logs across multiple services using trace IDs and timestamps", "complexity": "high"},
            {"name": "parquet-viewer", "type": "tool", "desc": "CLI viewer for Parquet files with filtering and aggregation", "complexity": "medium"},
        ]
    },
    {
        "domain": "Security",
        "problems": [
            {"name": "secret-scanner", "type": "cli", "desc": "Scan codebases for accidentally committed secrets, API keys, and credentials", "complexity": "high"},
            {"name": "cert-monitor", "type": "tool", "desc": "Monitor SSL certificate expiration across multiple domains", "complexity": "medium"},
            {"name": "dependency-fuzzer", "type": "tool", "desc": "Fuzz test dependencies for known vulnerability patterns", "complexity": "high"},
            {"name": "cors-checker", "type": "tool", "desc": "Test and validate CORS configurations across API endpoints", "complexity": "medium"},
        ]
    },
    {
        "domain": "DevOps Infrastructure",
        "problems": [
            {"name": "docker-size-optimizer", "type": "cli", "desc": "Analyze Docker images and suggest optimizations to reduce image size", "complexity": "high"},
            {"name": "k8s-cost-tracker", "type": "tool", "desc": "Track Kubernetes resource usage and estimate cloud costs per namespace", "complexity": "high"},
            {"name": "terraform-differ", "type": "tool", "desc": "Preview Terraform changes before apply with cost estimation", "complexity": "high"},
            {"name": "nginx-config-gen", "type": "cli", "desc": "Generate nginx configs from simple YAML declarations with rate limiting and caching", "complexity": "medium"},
            {"name": "health-dashboard", "type": "webapp", "desc": "Real-time service health dashboard with configurable checks and alerts", "complexity": "high"},
        ]
    },
    {
        "domain": "API Development",
        "problems": [
            {"name": "mock-server", "type": "tool", "desc": "Generate mock API servers from OpenAPI specs with realistic data", "complexity": "high"},
            {"name": "rate-limiter", "type": "library", "desc": "Sliding window rate limiter with Redis and in-memory backends", "complexity": "medium"},
            {"name": "api-versioner", "type": "library", "desc": "API versioning middleware with backward compatibility checks", "complexity": "medium"},
            {"name": "request-validator", "type": "library", "desc": "Runtime request validation with custom rules and error formatting", "complexity": "medium"},
            {"name": "graphql-stitcher", "type": "tool", "desc": "Stitch multiple GraphQL APIs into a unified gateway", "complexity": "high"},
        ]
    },
    {
        "domain": "Code Quality",
        "problems": [
            {"name": "complexity-analyzer", "type": "tool", "desc": "Analyze code complexity metrics (cyclomatic, cognitive) across a codebase", "complexity": "high"},
            {"name": "test-coverage-gap", "type": "tool", "desc": "Find untested code paths and suggest test cases based on code analysis", "complexity": "high"},
            {"name": "dead-code-finder", "type": "tool", "desc": "Detect unused exports, unreachable code, and orphaned files", "complexity": "high"},
            {"name": "dependency-graph", "type": "webapp", "desc": "Visualize module dependency graphs with circular dependency detection", "complexity": "high"},
            {"name": "code-review-bot", "type": "tool", "desc": "Automated code review with style, security, and performance checks", "complexity": "high"},
        ]
    },
    {
        "domain": "Cloud & Networking",
        "problems": [
            {"name": "dns-propagation-checker", "type": "cli", "desc": "Check DNS propagation across multiple global nameservers", "complexity": "medium"},
            {"name": "ssl-tester", "type": "cli", "desc": "Test SSL/TLS configurations with protocol and cipher analysis", "complexity": "medium"},
            {"name": "cdn-invalidator", "type": "cli", "desc": "Bulk invalidate CDN cache across Cloudflare, AWS CloudFront, and Fastly", "complexity": "medium"},
            {"name": "port-scanner", "type": "cli", "desc": "Fast async port scanner with service detection and reporting", "complexity": "medium"},
            {"name": "cloud-cost-comparator", "type": "tool", "desc": "Compare pricing across AWS, GCP, and Azure for given resource specs", "complexity": "high"},
        ]
    },
    {
        "domain": "Frontend Engineering",
        "problems": [
            {"name": "bundle-analyzer", "type": "tool", "desc": "Analyze JavaScript bundle size with tree-shaking suggestions", "complexity": "high"},
            {"name": "lighthouse-ci", "type": "tool", "desc": "Run Lighthouse audits in CI with regression detection", "complexity": "high"},
            {"name": "a11y-checker", "type": "tool", "desc": "Accessibility checker with WCAG compliance reporting", "complexity": "high"},
            {"name": "image-optimizer", "type": "cli", "desc": "Optimize images with format conversion, compression, and responsive sizing", "complexity": "medium"},
        ]
    },
]


def research_deep():
    all_projects = []
    for domain in PROBLEM_DOMAINS:
        for project in domain["problems"]:
            project["domain"] = domain["domain"]
            all_projects.append(project)

    try:
        trending = _fetch_github_trending()
        all_projects.extend(trending)
    except Exception:
        pass

    random.shuffle(all_projects)
    return all_projects


def pick_smart_project(domain=None, complexity=None):
    candidates = research_deep()

    if domain:
        candidates = [p for p in candidates if domain.lower() in p.get("domain", "").lower()]

    if complexity:
        candidates = [p for p in candidates if p.get("complexity") == complexity]

    if not candidates:
        candidates = research_deep()

    return random.choice(candidates)


def suggest_proProjects(count=8):
    all_projects = research_deep()

    high_complexity = [p for p in all_projects if p.get("complexity") == "high"]
    med_complexity = [p for p in all_projects if p.get("complexity") == "medium"]

    selected = []
    selected.extend(random.sample(high_complexity, min(count // 2, len(high_complexity))))
    selected.extend(random.sample(med_complexity, min(count - len(selected), len(med_complexity))))

    if len(selected) < count:
        remaining = [p for p in all_projects if p not in selected]
        selected.extend(random.sample(remaining, min(count - len(selected), len(remaining))))

    random.shuffle(selected)
    return selected[:count]


def get_domains():
    return [d["domain"] for d in PROBLEM_DOMAINS]


def get_projects_by_domain(domain):
    for d in PROBLEM_DOMAINS:
        if domain.lower() in d["domain"].lower():
            return d["problems"]
    return []


def _fetch_github_trending():
    topics = []
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f"created:>{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} stars:>50",
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
                name = repo.get("name", "")
                desc = repo.get("description", "") or ""
                if _is_useful_project(name, desc):
                    topics.append({
                        "name": _slugify(name),
                        "type": _guess_type(name, desc),
                        "desc": desc[:100],
                        "domain": "Community Trending",
                        "complexity": "medium",
                        "source": "github",
                    })
    except Exception:
        pass
    return topics


def _is_useful_project(name, desc):
    combined = (name + " " + desc).lower()
    skip_words = ["todo", "hello", "boilerplate", "starter", "example", "demo", "test", "fake", "mock"]
    return not any(w in combined for w in skip_words)


def _slugify(name):
    return name.lower().replace(" ", "-").replace("_", "-")[:20]


def _guess_type(name, desc):
    combined = (name + " " + desc).lower()
    if any(w in combined for w in ["cli", "command", "terminal", "console"]):
        return "cli"
    if any(w in combined for w in ["api", "server", "backend", "rest"]):
        return "api"
    if any(w in combined for w in ["web", "app", "dashboard", "ui"]):
        return "webapp"
    if any(w in combined for w in ["lib", "module", "package"]):
        return "library"
    return "tool"
