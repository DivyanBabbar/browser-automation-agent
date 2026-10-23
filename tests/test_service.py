from datetime import UTC, datetime

import pytest

from browser_agent import service, storage
from browser_agent.models import (
    AutomationPlan,
    AutomationStep,
    ExecuteRequest,
    PageSnapshot,
    PlanResponse,
)
from browser_agent.planner import ApprovalRequired


def test_execution_requires_approval_and_persists_simulated_results(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "data_dir", str(tmp_path))
    storage.initialize_database()
    run = PlanResponse(
        run_id="run-42",
        status="planned",
        start_url="https://example.org/",
        goal="Open the contact panel and read its text.",
        allowed_domains=["example.org"],
        snapshot=PageSnapshot(
            title="Example",
            url="https://example.org/",
            text="Example Domain",
            controls=[],
            screenshot_url="/runs/run-42/screenshots/before",
        ),
        plan=AutomationPlan(
            summary="Open the contact panel and read the result.",
            steps=[
                AutomationStep(
                    id="open",
                    action="click",
                    selector="#contact",
                    rationale="Open the requested panel",
                ),
                AutomationStep(
                    id="read",
                    action="extract_text",
                    selector="main",
                    rationale="Read the panel text",
                ),
            ],
        ),
        created_at=datetime.now(UTC),
    )
    storage.save_run(run)
    monkeypatch.setattr(
        service,
        "execute_plan",
        lambda *_args: [{"step_id": "read", "action": "extract_text", "result": "Contact us"}],
    )

    with pytest.raises(ApprovalRequired):
        service.execute_run(run.run_id, ExecuteRequest())

    result = service.execute_run(run.run_id, ExecuteRequest(approved_step_ids=["open"]))

    assert result.status == "completed"
    assert result.execution[0]["result"] == "Contact us"
    assert storage.get_run(run.run_id) == result
    with pytest.raises(ValueError, match="cannot be executed"):
        service.execute_run(run.run_id, ExecuteRequest(approved_step_ids=["open"]))
