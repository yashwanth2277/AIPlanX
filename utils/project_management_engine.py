
from datetime import datetime, timezone

from schemas.project_management import (
    DelayRecord,
    ProjectManagementState,
    TaskActivity,
    TaskProgress,
    TaskStatus,
)


def update_task_progress(
    state: ProjectManagementState,
    task_id: int,
    status: TaskStatus,
    progress_percent: float,
    actual_hours_spent: float | None = None,
    completed_work: str | None = None,
    remaining_work: str | None = None,
    blockers: list[str] | None = None,
    comment: str | None = None,
    updated_by: str = "Unspecified",
    updater_role: str | None = None,
) -> ProjectManagementState:
    """Update task progress and preserve a permanent activity history."""

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

    updated_at = datetime.now(timezone.utc)

    new_hours = (
        actual_hours_spent
        if actual_hours_spent is not None
        else current.actual_hours_spent
    )

    new_blockers = (
        blockers
        if blockers is not None
        else current.blockers
    )
    new_completed_work = (
        completed_work
        if completed_work is not None
        else current.completed_work
    )

    new_remaining_work = (
        remaining_work
        if remaining_work is not None
        else current.remaining_work
    )

    new_comment = (
        comment
        if comment is not None
        else current.comment
    )

    updated_record = TaskProgress(
        task_id=current.task_id,
        status=status,
        progress_percent=progress_percent,
        actual_hours_spent=new_hours,
        completed_work=new_completed_work,
        remaining_work=new_remaining_work,
        blockers=new_blockers,
        comment=new_comment,
        delays=current.delays,
        updated_at=updated_at,
    )

    activity = TaskActivity(
        task_id=task_id,
        updated_by=updated_by,
        updater_role=updater_role,
        status=status,
        progress_percent=progress_percent,
        actual_hours_spent=new_hours,
        completed_work=new_completed_work,
        remaining_work=new_remaining_work,
        blockers=new_blockers,
        comment=new_comment,
        recorded_at=updated_at,
    )

    updated_records = [
        updated_record if record.task_id == task_id else record
        for record in state.task_progress
    ]

    return ProjectManagementState(
        plan=state.plan,
        task_progress=updated_records,
        assignments=state.assignments,
        assignment_changes=state.assignment_changes,
        applied_delay_ids=state.applied_delay_ids,
        activity_history=[
            *state.activity_history,
            activity,
        ],
    )


def record_task_delay(
    state: ProjectManagementState,
    task_id: int,
    delay_hours: float,
    reason: str,
) -> ProjectManagementState:
    """Record a delay without modifying the original state."""

    progress_records = {
        record.task_id: record
        for record in state.task_progress
    }

    if task_id not in progress_records:
        raise ValueError(f"Unknown task ID: {task_id}")

    current = progress_records[task_id]

    delay = DelayRecord(
        task_id=task_id,
        delay_hours=delay_hours,
        reason=reason,
    )

    updated_record = TaskProgress(
        task_id=current.task_id,
        status=current.status,
        progress_percent=current.progress_percent,
        actual_hours_spent=current.actual_hours_spent,
        completed_work=current.completed_work,
        remaining_work=current.remaining_work,
        blockers=current.blockers,
        comment=current.comment,
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
        assignments=state.assignments,
        assignment_changes=state.assignment_changes,
        applied_delay_ids=state.applied_delay_ids,
        activity_history=state.activity_history,
    )
