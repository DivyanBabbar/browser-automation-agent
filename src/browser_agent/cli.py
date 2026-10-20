import argparse
import json

from browser_agent.models import ExecuteRequest, PlanRequest
from browser_agent.service import execute_run, plan_run
from browser_agent.storage import initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan browser workflows with step-level approvals.")
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="Inspect a page and create a saved action plan")
    plan.add_argument("url")
    plan.add_argument("goal")
    plan.add_argument("--allow-domain", action="append", default=[])
    plan.add_argument("--max-steps", type=int, default=6)
    execute = commands.add_parser("execute", help="Execute a saved plan after approving its steps")
    execute.add_argument("run_id")
    execute.add_argument("--approve-step", action="append", default=[])
    args = parser.parse_args()
    initialize_database()
    if args.command == "plan":
        result = plan_run(
            PlanRequest(
                start_url=args.url,
                goal=args.goal,
                allowed_domains=args.allow_domain,
                max_steps=args.max_steps,
            )
        )
    else:
        result = execute_run(args.run_id, ExecuteRequest(approved_step_ids=args.approve_step))
    print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
