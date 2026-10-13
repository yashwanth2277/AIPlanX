
from pydantic import BaseModel, Field, model_validator


class Subtask(BaseModel):
    subtask_id: int
    title: str
    description: str
    estimated_hours: float = Field(gt=0)


class TaskBreakdown(BaseModel):
    task_id: int
    task_title: str
    parent_estimated_hours: float = Field(gt=0)
    subtasks: list[Subtask] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_subtask_hours(self):
        total = sum(subtask.estimated_hours for subtask in self.subtasks)

        if abs(total - self.parent_estimated_hours) > 0.1:
            raise ValueError(
                f"Subtask hours total ({total}) must match "
                f"parent task hours ({self.parent_estimated_hours})"
            )

        return self
