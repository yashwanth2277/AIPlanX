
from pydantic import BaseModel, Field, model_validator


class ScheduledTask(BaseModel):
    task_id: int
    title: str
    estimated_hours: float = Field(gt=0)
    start_day: int = Field(ge=1)
    end_day: int = Field(ge=1)
    dependencies: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_day_range(self):
        if self.end_day < self.start_day:
            raise ValueError("end_day cannot be before start_day")
        return self


class ProjectSchedule(BaseModel):
    project_name: str
    total_duration_days: int = Field(gt=0)
    critical_path: list[int] = Field(min_length=1)
    scheduled_tasks: list[ScheduledTask] = Field(min_length=1)
    scheduling_notes: list[str] = Field(default_factory=list)
