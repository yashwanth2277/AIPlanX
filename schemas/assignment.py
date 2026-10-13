
from pydantic import BaseModel, Field


class TaskAssignment(BaseModel):
    task_id: int
    task_title: str
    employee_id: str
    employee_name: str
    match_score: float = Field(ge=0, le=1)
    assignment_reason: str


class UnassignedTask(BaseModel):
    task_id: int
    task_title: str
    reason: str


class AssignmentReport(BaseModel):
    assignments: list[TaskAssignment] = Field(default_factory=list)
    unassigned_tasks: list[UnassignedTask] = Field(default_factory=list)
