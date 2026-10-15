
from pydantic import BaseModel, Field

from schemas.project_management import TaskStatus


class TaskProgressSummary(BaseModel):
    """Summary of task progress by status."""

    total_tasks: int = Field(ge=0)
    pending_tasks: int = Field(ge=0)
    in_progress_tasks: int = Field(ge=0)
    blocked_tasks: int = Field(ge=0)
    completed_tasks: int = Field(ge=0)


class TaskDelaySummary(BaseModel):
    """Summary of a recorded task delay."""

    task_id: int
    task_title: str
    delay_hours: float = Field(ge=0)
    reason: str


class ManagementReport(BaseModel):
    """Live status report for project management."""

    project_name: str
    progress: TaskProgressSummary
    task_delays: list[TaskDelaySummary] = Field(default_factory=list)
    schedule_impact: dict | None = None
    revised_completion_week: int | None = Field(default=None, ge=1)
    task_statuses: dict[int, TaskStatus] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
