
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from schemas.project_plan import ProjectPlan
from schemas.assignment import TaskAssignment


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class DelayRecord(BaseModel):
    task_id: int
    delay_hours: float = Field(gt=0)
    reason: str = Field(min_length=3)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class TaskProgress(BaseModel):
    task_id: int
    status: TaskStatus = TaskStatus.PENDING
    progress_percent: float = Field(default=0, ge=0, le=100)
    actual_hours_spent: float = Field(default=0, ge=0)
    delays: list[DelayRecord] = Field(default_factory=list)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @model_validator(mode="after")
    def validate_completed_progress(self):
        if self.status == TaskStatus.COMPLETED:
            if self.progress_percent != 100:
                raise ValueError(
                    "Completed tasks must have 100% progress"
                )
        elif self.progress_percent == 100:
            raise ValueError(
                "Tasks with 100% progress must be completed"
            )

        return self


class AssignmentChange(BaseModel):
    task_id: int
    previous_employee_id: str | None = None
    new_employee_id: str = Field(min_length=1)
    reason: str = Field(min_length=3)
    changed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )



class ProjectManagementState(BaseModel):
    plan: ProjectPlan
    task_progress: list[TaskProgress] = Field(min_length=1)
    assignments: list[TaskAssignment] = Field(default_factory=list)
    assignment_changes: list[AssignmentChange] = Field(
        default_factory=list
    )
    applied_delay_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_applied_delay_ids(self):
        if len(self.applied_delay_ids) != len(set(self.applied_delay_ids)):
            raise ValueError("Applied delay IDs must be unique")
        return self

    @model_validator(mode="after")
    def validate_task_records(self):
        plan_task_ids = {task.task_id for task in self.plan.tasks}
        progress_task_ids = [
            task.task_id for task in self.task_progress
        ]

        if len(progress_task_ids) != len(set(progress_task_ids)):
            raise ValueError("Task progress records must have unique IDs")

        if set(progress_task_ids) != plan_task_ids:
            raise ValueError(
                "Progress records must exist for every planned task "
                "and no other tasks"
            )

        assignment_task_ids = [
            assignment.task_id for assignment in self.assignments
        ]

        if len(assignment_task_ids) != len(set(assignment_task_ids)):
            raise ValueError("Each task can have only one current assignment")

        for task_id in assignment_task_ids:
            if task_id not in plan_task_ids:
                raise ValueError(
                    f"Assignment references unknown task {task_id}"
                )

        for delay in (
            delay
            for progress in self.task_progress
            for delay in progress.delays
        ):
            if delay.task_id not in plan_task_ids:
                raise ValueError(
                    f"Delay references unknown task {delay.task_id}"
                )

        for change in self.assignment_changes:
            if change.task_id not in plan_task_ids:
                raise ValueError(
                    f"Assignment change references unknown task "
                    f"{change.task_id}"
                )

        return self
