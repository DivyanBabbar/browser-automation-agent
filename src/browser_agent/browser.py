from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Route, sync_playwright

from browser_agent.config import settings
from browser_agent.models import AutomationPlan, PageSnapshot
from browser_agent.safety import BrowserPolicyError, validate_fill_target, validate_url

MAX_PAGE_TEXT = 12_000
MAX_CONTROLS = 50


def _guarded_context(browser: Browser, allowed_domains: list[str]) -> BrowserContext:
    context = browser.new_context(accept_downloads=False, service_workers="block")

    def guard(route: Route) -> None:
        try:
            validate_url(route.request.url, allowed_domains, resolve_dns=True)
        except BrowserPolicyError:
            route.abort("blockedbyclient")
        else:
            route.continue_()

    context.route("**/*", guard)
    return context


def _read_page(page: Page) -> tuple[str, list[dict[str, str]]]:
    text = page.locator("body").inner_text(timeout=settings.browser_timeout_ms)
    controls: list[dict[str, str]] = page.locator(
        "a, button, input, textarea, select, [role='button']"
    ).evaluate_all(
        """elements => elements.slice(0, 50).map((el) => ({
            tag: el.tagName.toLowerCase(),
            text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 180),
            id: el.id || '',
            name: el.getAttribute('name') || '',
            type: el.getAttribute('type') || '',
            placeholder: el.getAttribute('placeholder') || '',
            href: el.getAttribute('href') || ''
        }))"""
    )
    return text[:MAX_PAGE_TEXT], controls[:MAX_CONTROLS]


def inspect_page(run_id: str, url: str, allowed_domains: list[str]) -> PageSnapshot:
    validate_url(url, allowed_domains)
    screenshot = Path(settings.data_dir) / "screenshots" / f"{run_id}-before.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = _guarded_context(browser, allowed_domains)
            try:
                page = context.new_page()
                page.set_default_timeout(settings.browser_timeout_ms)
                page.goto(url, wait_until="domcontentloaded", timeout=settings.browser_timeout_ms)
                text, controls = _read_page(page)
                page.screenshot(path=str(screenshot), full_page=True, animations="disabled")
                return PageSnapshot(
                    title=page.title()[:300],
                    url=page.url,
                    text=text,
                    controls=controls,
                    screenshot_url=f"/runs/{run_id}/screenshots/before",
                )
            finally:
                context.close()
        finally:
            browser.close()


def execute_plan(
    run_id: str,
    url: str,
    allowed_domains: list[str],
    plan: AutomationPlan,
) -> list[dict[str, str]]:
    validate_url(url, allowed_domains)
    screenshot = Path(settings.data_dir) / "screenshots" / f"{run_id}-after.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = _guarded_context(browser, allowed_domains)
            try:
                page = context.new_page()
                page.set_default_timeout(settings.browser_timeout_ms)
                page.goto(url, wait_until="domcontentloaded", timeout=settings.browser_timeout_ms)
                for step in plan.steps:
                    locator = page.locator(step.selector).first if step.selector else None
                    output = ""
                    if step.action == "click":
                        locator.click()
                        output = f"Clicked {step.selector}"
                    elif step.action == "fill":
                        _assert_fill_target(locator)
                        locator.fill(step.value or "")
                        output = f"Filled {step.selector}"
                    elif step.action == "extract_text":
                        output = locator.inner_text()[:3000]
                    elif step.action == "wait":
                        page.wait_for_timeout(step.wait_ms or 0)
                        output = f"Waited {step.wait_ms or 0} ms"
                    results.append(
                        {"step_id": step.id, "action": step.action, "result": output, "url": page.url}
                    )
                page.screenshot(path=str(screenshot), full_page=True, animations="disabled")
                return results
            finally:
                context.close()
        finally:
            browser.close()


def screenshot_path(run_id: str, phase: str) -> Path:
    if phase not in {"before", "after"}:
        raise ValueError("Screenshot phase must be before or after.")
    return Path(settings.data_dir) / "screenshots" / f"{run_id}-{phase}.png"


def _assert_fill_target(locator: Any) -> None:
    attributes = locator.evaluate(
        "el => ({type:el.getAttribute('type'),name:el.getAttribute('name'),id:el.id," 
        "placeholder:el.getAttribute('placeholder'),autocomplete:el.getAttribute('autocomplete')," 
        "'aria-label':el.getAttribute('aria-label')})"
    )
    validate_fill_target(attributes)
