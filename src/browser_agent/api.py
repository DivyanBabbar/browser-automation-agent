import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from browser_agent.browser import screenshot_path
from browser_agent.config import settings
from browser_agent.models import ExecuteRequest, HistoryItem, PlanRequest, PlanResponse
from browser_agent.planner import ApprovalRequired, ConfigurationError, PlanningError
from browser_agent.safety import BrowserPolicyError
from browser_agent.service import execute_run, plan_run
from browser_agent.storage import get_run, initialize_database, list_runs

logging.basicConfig(level=settings.log_level.upper())
ASSET_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(
    title="Browser Automation Agent",
    summary="Plan and execute browser workflows with explicit approval for state-changing actions.",
    description=(
        "A constrained browser agent that inspects a page, proposes a typed action plan, "
        "and requires step-level approval before clicks or form fills."
    ),
    version="1.0.0",
    license_info={"name": "MIT"},
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=ASSET_DIR / "static"), name="static")
templates = Jinja2Templates(directory=ASSET_DIR / "templates")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"history": list_runs(10)},
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": "browser-agent"}


@app.get("/history", response_model=list[HistoryItem], tags=["runs"])
def history(limit: int = Query(default=20, ge=1, le=100)) -> list[HistoryItem]:
    return list_runs(limit)


@app.post("/runs", response_model=PlanResponse, tags=["runs"])
def create_run(request: PlanRequest) -> PlanResponse:
    try:
        return plan_run(request)
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BrowserPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PlanningError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logging.getLogger(__name__).exception("Planning run failed")
        raise HTTPException(status_code=502, detail="Could not inspect the page or create a plan.") from exc


@app.get("/runs/{run_id}", response_model=PlanResponse, tags=["runs"])
def get_run_detail(run_id: str) -> PlanResponse:
    result = get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return result


@app.post("/runs/{run_id}/execute", response_model=PlanResponse, tags=["runs"])
def execute(run_id: str, request: ExecuteRequest) -> PlanResponse:
    try:
        return execute_run(run_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalRequired as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "required_step_ids": exc.step_ids},
        ) from exc
    except BrowserPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logging.getLogger(__name__).exception("Execution failed")
        raise HTTPException(status_code=502, detail="The browser run failed. Check server logs.") from exc


@app.get("/runs/{run_id}/screenshots/{phase}", tags=["runs"])
def screenshot(run_id: str, phase: str) -> FileResponse:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    path = screenshot_path(run_id, phase)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found.")
    return FileResponse(path, media_type="image/png", filename=f"{run_id}-{phase}.png")
