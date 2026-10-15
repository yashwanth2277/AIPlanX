
from datetime import datetime, timezone

from schemas.project_management import (
    DelayRecord,
    ProjectManagementState,
    TaskProgress,
    TaskStatus,
)


def update_task_progress(
    state: ProjectManagementState,
    task_id: int,
    status: TaskStatus,
    progress_percent: float,
    actual_hours_spent: float | None = None,
) -> ProjectManagementState:
    """Update one task's progress without modifying the original state."""

    plan_tasks = {
        task.task_id: task
        for task in state.plan.tasks
    }

    progress_records = {
        record.task_id: record
        for record in state.task_progress
    }

    if task_id not in plan_tasks:
        raise ValueError(f"Unknown task ID: {task_id}")

    current = progress_records[task_id]

    if current.status == TaskStatus.COMPLETED:
        raise ValueError("Completed tasks cannot be updated")

    if actual_hours_spent is not None and actual_hours_spent < 0:
        raise ValueError("Actual hours cannot be negative")

    if status == TaskStatus.COMPLETED:
        if progress_percent != 100:
            raise ValueError("Completed tasks require 100% progress")

        for dependency_id in plan_tasks[task_id].dependencies:
            dependency = progress_records[dependency_id]

            if dependency.status != TaskStatus.COMPLETED:
                raise ValueError(
                    f"Cannot complete task {task_id}: "
                    f"dependency {dependency_id} is not completed"
                )

    # Construct a new Pydantic model so validation is applied.
    updated_record = TaskProgress(
        task_id=current.task_id,
        status=status,
        progress_percent=progress_percent,
        actual_hours_spent=(
            actual_hours_spent
            if actual_hours_spent is not None
            else current.actual_hours_spent
        ),
        delays=current.delays,
        updated_at=datetime.now(timezone.utc),
    )

    updated_records = [
        updated_record if record.task_id == task_id else record
        for record in state.task_progress
    ]

    return ProjectManagementState(
        plan=state.plan,
        task_progress=updated_records,
        assignment_changes=state.assignment_changes,
    )


def record_task_delay(
    state: ProjectManagementState,
    task_id: int,
    delay_hours: float,
    reason: str,
) -> ProjectManagementState:
    """Record a delay for a known task without modifying the original state."""

    progress_records = {
        record.task_id: record
        for record in state.task_progress
    }

    if task_id not in progress_records:
        raise ValueError(f"Unknown task ID: {task_id}")

    current = progress_records[task_id]

    # Validate delay hours and reason through the Pydantic model.
    delay = DelayRecord(
        task_id=task_id,
        delay_hours=delay_hours,
        reason=reason,
    )

    # Reconstruct the model to validate the updated record.
    updated_record = TaskProgress(
        task_id=current.task_id,
        status=current.status,
        progress_percent=current.progress_percent,
        actual_hours_spent=current.actual_hours_spent,
        delays=[*current.delays, delay],
        updated_at=datetime.now(timezone.utc),
    )

    updated_records = [
        updated_record if record.task_id == task_id else record
        for record in state.task_progress
    ]

    return ProjectManagementState(
        plan=state.plan,
        task_progress=updated_records,
        ssignments=state.assignments,
        assignment_changes=state.assignment_changes,
        applied_delay_ids=state.applied_delay_ids,
    )
