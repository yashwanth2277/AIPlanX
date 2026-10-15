
from typing import TypedDict

from schemas.employee import Employee
from schemas.management_ai import ManagementAIInsights
from schemas.project_management import (
    ProjectManagementState,
    TaskStatus,
)
from schemas.work_schedule import WorkSchedule
from utils.schedule_impact_engine import ScheduleImpactReport


class ManagementWorkflowState(TypedDict, total=False):
    """State passed between live project management workflow nodes."""

    # Main management state
    management_state: ProjectManagementState
    action: str

    # Employees and scheduling
    employees: list[Employee]
    work_schedule: WorkSchedule
    schedule_impact_report: ScheduleImpactReport

    # Task progress updates
    update_task_id: int
    update_task_status: TaskStatus
    update_progress_percent: float
    update_actual_hours_spent: float | None

    # Delay recording
    delay_task_id: int
    delay_hours: float
    delay_reason: str

    # Schedule impact and rescheduling
    delayed_task_id: int
    delay_weeks: int

    # Task reassignment
    reassign_task_id: int
    new_employee_id: str
    reassignment_reason: str

    # Management reports
    management_report: dict
    management_ai_insights: ManagementAIInsights
