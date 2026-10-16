from datetime import datetime

from pydantic import BaseModel, Field

from schemas.employee import Employee
from schemas.final_report import FinalProjectReport
from schemas.project_management import ProjectManagementState
from schemas.work_schedule import WorkSchedule


class ProjectRecord(BaseModel):
    id: int
    name: str
    summary: str = ""
    description: str = ""
    created_at: datetime
    final_report: FinalProjectReport | None = None
    team_workflow: dict | None = None


class SessionRecord(BaseModel):
    name: str
    project_id: int | None = None
    created_at: datetime
    updated_at: datetime
    management_state: ProjectManagementState
    work_schedule: WorkSchedule


class SessionSummary(BaseModel):
    name: str
    project_id: int | None = None
    project_name: str
    task_count: int = 0
    updated_at: datetime


class EmployeeList(BaseModel):
    employees: list[Employee] = Field(default_factory=list)
