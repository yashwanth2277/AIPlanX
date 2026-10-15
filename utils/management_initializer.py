from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
    TaskStatus,
)
from schemas.project_plan import ProjectPlan
from schemas.assignment import TaskAssignment


def initialize_management_state(
    plan: ProjectPlan,
    assignments: list[TaskAssignment] | None = None,
) -> ProjectManagementState:
    """Initialize live management records for every planned task."""

    progress_records = [
        TaskProgress(
            task_id=task.task_id,
            status=TaskStatus.PENDING,
            progress_percent=0,
            actual_hours_spent=0,
        )
        for task in plan.tasks
    ]

    return ProjectManagementState(
        plan=plan,
        task_progress=progress_records,
        assignments=assignments or [],
        assignment_changes=[],
    )