from datetime import UTC, datetime

from browser_agent.browser import execute_plan
from browser_agent.models import ExecuteRequest, PlanRequest, PlanResponse
from browser_agent.planner import ApprovalRequired, create_plan, validate_approvals
from browser_agent.storage import claim_run, get_run, save_run, update_run


def plan_run(request: PlanRequest) -> PlanResponse:
    run_id, domains, snapshot, plan = create_plan(request)
    result = PlanResponse(
        run_id=run_id,
        status="planned",
        start_url=str(request.start_url),
        goal=request.goal,
        allowed_domains=domains,
        snapshot=snapshot,
        plan=plan,
        created_at=datetime.now(UTC),
    )
    save_run(result)
    return result


def execute_run(run_id: str, request: ExecuteRequest) -> PlanResponse:
    run = get_run(run_id)
    if run is None:
        raise KeyError("Run not found.")
    if run.status != "planned":
        raise ValueError(f"This run cannot be executed from status '{run.status}'.")
    validate_approvals(run.plan, request.approved_step_ids)
    if not claim_run(run_id):
        raise ValueError("This run has already been claimed for execution.")
    run.status = "running"
    update_run(run)
    try:
        run.execution = execute_plan(run_id, run.start_url, run.allowed_domains, run.plan)
        run.status = "completed"
    except Exception as exc:
        run.status = "failed"
        run.execution = [{"step_id": "error", "action": "error", "result": str(exc)[:500]}]
        update_run(run)
        raise
    update_run(run)
    return run
