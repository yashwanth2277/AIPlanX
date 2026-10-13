
from pydantic import BaseModel, Field


class WeeklyAllocation(BaseModel):
    week: int = Field(ge=1)
    allocated_hours: float = Field(gt=0)


class ScheduledTask(BaseModel):
    task_id: int
    task_title: str
    employee_id: str
    employee_name: str
    total_estimated_hours: float = Field(gt=0)
    weekly_allocations: list[WeeklyAllocation] = Field(min_length=1)
    start_week: int = Field(ge=1)
    completion_week: int = Field(ge=1)
    assignment_reason: str


class WorkSchedule(BaseModel):
    scheduled_tasks: list[ScheduledTask] = Field(default_factory=list)
    unscheduled_tasks: list[dict] = Field(default_factory=list)
