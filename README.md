# Waypoint — Browser Automation Agent

Waypoint turns a plain-language browser task into a reviewable plan. It inspects one approved website, proposes bounded browser actions, and pauses for explicit approval before clicks or form fills.

![CI](https://github.com/DivyanBabbar/browser-automation-agent/actions/workflows/ci.yml/badge.svg)

## Why this project

Browser automation is useful when it is observable and controllable. Waypoint demonstrates a human-in-the-loop agent with domain allowlisting, sensitive-field blocking, run history, screenshots, and a small auditable action vocabulary.

## Features

- FastAPI service and responsive web console
- OpenAI Responses API planner that treats page content as untrusted input
- Playwright Chromium inspection and execution
- Step-by-step approval for every click and form fill
- Exact hostname allowlists and private-network / SSRF protections on navigations and requests
- Password, payment, hidden, file, token, and one-time-code fields are blocked
- SQLite run history, screenshots, CLI, Docker Compose, OpenAPI docs
- GitHub Actions quality checks and CodeQL

## Quick start

Requirements: Python 3.11+, an OpenAI API key, and Chromium dependencies. Docker Compose is the easiest setup.

```bash
git clone https://github.com/DivyanBabbar/browser-automation-agent.git
cd browser-automation-agent
cp .env.example .env
# Add OPENAI_API_KEY to .env
docker compose up --build
```

Open <http://localhost:8000>. Enter a public page URL, describe the task, and optionally add exact hostnames for resources the page needs. Review the plan and approve each state-changing action before execution. API docs are at `/docs`.

### Local development

```bash
python -m venv .venv
# Activate the environment, then:
pip install -e '.[dev]'
playwright install chromium
cp .env.example .env
browser-agent serve
```

## Safety model

Waypoint is a demonstration agent, not an unattended account operator. It only supports `click`, `fill`, `extract_text`, and bounded `wait`. Click and fill require individual approvals; secrets and sensitive fields are refused. URLs must use HTTP(S), match an exact approved hostname, and resolve to public addresses. Redirects and browser requests are checked against the allowlist. Keep the service on a trusted network and do not expose it publicly without authentication, TLS, rate limits, and deployment-specific security review.

Page content is untrusted and may contain prompt injection. The planner is instructed to ignore page instructions, and execution is constrained by typed actions and policy checks. This is defense in depth, not a guarantee against every browser or model vulnerability.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for planning |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Responses API model |
| `BROWSER_TIMEOUT_MS` | `12000` | Navigation/action timeout |
| `MAX_PLAN_STEPS` | `8` | Server-side action cap |
| `DATA_DIR` | `data` | SQLite and screenshot storage |
| `LOG_LEVEL` | `INFO` | Application log level |

## API

- `POST /runs` inspect a URL and create a bounded plan
- `GET /runs/{run_id}` retrieve a plan and execution state
- `POST /runs/{run_id}/execute` execute approved step IDs
- `GET /history` list recent runs
- `GET /health` readiness check

## Development

```bash
ruff check .
ruff format --check .
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CHANGELOG.md](CHANGELOG.md). Licensed under MIT.
