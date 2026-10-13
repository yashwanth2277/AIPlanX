from pydantic import BaseModel, Field


class TaskProgress(BaseModel):
    task_id: int
    task_title: str
    planned_hours: float = Field(gt=0)
    actual_hours: float = Field(ge=0)
    status: str
    progress_percentage: float = Field(ge=0, le=100)
    blockers: list[str] = Field(default_factory=list)


class ProgressReport(BaseModel):
    project_name: str
    overall_progress_percentage: float = Field(ge=0, le=100)
    completed_tasks: int = Field(ge=0)
    pending_tasks: int = Field(ge=0)
    delayed_tasks: list[int] = Field(default_factory=list)
    task_progress: list[TaskProgress] = Field(min_length=1)
    recommendations: list[str] = Field(default_factory=list)