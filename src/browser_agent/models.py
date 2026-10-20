from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, computed_field, model_validator


class PlanRequest(BaseModel):
    start_url: HttpUrl
    goal: str = Field(min_length=8, max_length=1200)
    allowed_domains: list[str] = Field(default_factory=list, max_length=10)
    max_steps: int = Field(default=6, ge=1, le=12)


class PageSnapshot(BaseModel):
    title: str
    url: str
    text: str
    controls: list[dict[str, str]]
    screenshot_url: str


class AutomationStep(BaseModel):
    id: str = Field(min_length=1, max_length=20, pattern="^[a-zA-Z0-9_-]+$")
    action: Literal["click", "fill", "extract_text", "wait"]
    selector: str = Field(default="", max_length=400)
    value: str | None = Field(default=None, max_length=2000)
    wait_ms: int | None = Field(default=None, ge=0, le=5000)
    rationale: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def validate_action_fields(self) -> "AutomationStep":
        if self.action in {"click", "fill", "extract_text"} and not self.selector.strip():
            raise ValueError(f"{self.action} requires a CSS selector")
        if self.action == "fill" and self.value is None:
            raise ValueError("fill requires a value")
        if self.action == "wait" and self.wait_ms is None:
            raise ValueError("wait requires wait_ms")
        if self.selector.startswith(("xpath=", "text=", "javascript:")) or ">>" in self.selector:
            raise ValueError("Only plain CSS selectors are allowed")
        return self

    @computed_field
    @property
    def requires_approval(self) -> bool:
        return self.action in {"click", "fill"}


class AutomationPlan(BaseModel):
    summary: str = Field(min_length=1, max_length=600)
    steps: list[AutomationStep] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def unique_step_ids(self) -> "AutomationPlan":
        ids = [step.id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Step IDs must be unique")
        return self


class PlanResponse(BaseModel):
    run_id: str
    status: Literal["planned", "running", "completed", "failed"]
    start_url: str
    goal: str
    allowed_domains: list[str]
    snapshot: PageSnapshot
    plan: AutomationPlan
    execution: list[dict[str, str]] = Field(default_factory=list)
    created_at: datetime


class ExecuteRequest(BaseModel):
    approved_step_ids: list[str] = Field(default_factory=list, max_length=12)


class HistoryItem(BaseModel):
    run_id: str
    goal: str
    start_url: str
    status: Literal["planned", "running", "completed", "failed"]
    created_at: datetime
