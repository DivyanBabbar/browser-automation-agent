from datetime import UTC, datetime

from browser_agent import storage
from browser_agent.models import AutomationPlan, AutomationStep, PageSnapshot, PlanResponse


def test_run_round_trips_through_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "data_dir", str(tmp_path))
    storage.initialize_database()
    run = PlanResponse(
        run_id="run-42",
        status="planned",
        start_url="https://example.org/",
        goal="Read the top heading and report it.",
        allowed_domains=["example.org"],
        snapshot=PageSnapshot(
            title="Example",
            url="https://example.org/",
            text="Example Domain",
            controls=[],
            screenshot_url="/runs/run-42/screenshots/before",
        ),
        plan=AutomationPlan(
            summary="Read the page heading.",
            steps=[AutomationStep(id="read", action="extract_text", selector="h1", rationale="Get title")],
        ),
        created_at=datetime.now(UTC),
    )

    storage.save_run(run)

    assert storage.get_run(run.run_id) == run
    assert storage.list_runs(1)[0].run_id == run.run_id
    assert storage.claim_run(run.run_id) is True
    assert storage.claim_run(run.run_id) is False
