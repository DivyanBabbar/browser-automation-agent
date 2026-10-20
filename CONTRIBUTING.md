# Contributing

Thanks for helping improve Waypoint. Keep changes focused, explain the user-facing impact, and add or update tests for behavior changes.

## Setup

Use Python 3.11+, `pip install -e '.[dev]'`, and `playwright install chromium`.

## Checks

Run `ruff check .`, `ruff format --check .`, and `pytest` before opening a pull request. Do not commit `.env`, credentials, browser profiles, screenshots, or production data.

## Pull requests

Describe the problem, approach, safety implications, and how you verified the change. Changes that expand browser capabilities should include explicit policy tests and documentation.
