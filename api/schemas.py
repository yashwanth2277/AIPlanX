from pydantic import BaseModel, Field

from schemas.project_management import TaskStatus


class PlanRequest(BaseModel):
    description: str = Field(min_length=10, max_length=8000)
    session_name: str | None = Field(default=None, max_length=64)
    create_session: bool = True


class CreateSessionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    project_id: int | None = None


class ProgressUpdateRequest(BaseModel):
    status: TaskStatus
    progress_percent: float = Field(ge=0, le=100)
    actual_hours_spent: float | None = Field(default=None, ge=0)


class DelayRequest(BaseModel):
    delay_hours: float = Field(gt=0)
    reason: str = Field(min_length=3, max_length=2000)


class AnalyzeDelayRequest(BaseModel):
    delay_weeks: int = Field(ge=1, le=52)
    delay_hours: float | None = Field(default=None, gt=0)
    delay_reason: str | None = Field(default=None, min_length=3, max_length=2000)


class ReassignRequest(BaseModel):
    employee_id: str = Field(min_length=1)
    reason: str = Field(min_length=3, max_length=2000)


class AssistantAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    session_name: str = Field(min_length=1, max_length=64)
