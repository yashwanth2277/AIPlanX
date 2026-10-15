
from schemas.management_report import (
    ManagementReport,
    TaskDelaySummary,
    TaskProgressSummary,
)
from schemas.project_management import ProjectManagementState, TaskStatus
from schemas.work_schedule import WorkSchedule
from utils.schedule_impact_engine import ScheduleImpactReport


def generate_management_report(
    management_state: ProjectManagementState,
    work_schedule: WorkSchedule | None = None,
    schedule_impact: ScheduleImpactReport | None = None,
) -> ManagementReport:
    """Generate a structured report from the current management state."""

    task_titles = {
        task.task_id: task.title
        for task in management_state.plan.tasks
    }

    progress_records = management_state.task_progress

    status_counts = {
        status: sum(
            record.status == status
            for record in progress_records
        )
        for status in TaskStatus
    }

    progress = TaskProgressSummary(
        total_tasks=len(progress_records),
        pending_tasks=status_counts.get(TaskStatus.PENDING, 0),
        in_progress_tasks=status_counts.get(TaskStatus.IN_PROGRESS, 0),
        blocked_tasks=status_counts.get(TaskStatus.BLOCKED, 0),
        completed_tasks=status_counts.get(TaskStatus.COMPLETED, 0),
    )

    task_delays = [
        TaskDelaySummary(
            task_id=record.task_id,
            task_title=task_titles[record.task_id],
            delay_hours=delay.delay_hours,
            reason=delay.reason,
        )
        for record in progress_records
        for delay in record.delays
    ]

    revised_completion_week = (
        max(
            task.completion_week
            for task in work_schedule.scheduled_tasks
        )
        if work_schedule and work_schedule.scheduled_tasks
        else None
    )

    recommendations = []

    if progress.blocked_tasks:
        recommendations.append(
            "Review blocked tasks and resolve their blockers."
        )

    if task_delays:
        recommendations.append(
            "Review recorded delays and their effect on project delivery."
        )

    if schedule_impact and schedule_impact.project_delay_weeks > 0:
        recommendations.append(
            "Consider mitigation actions to reduce the projected project delay."
        )

    if not recommendations:
        recommendations.append(
            "Continue monitoring task progress and project delivery."
        )

    return ManagementReport(
        project_name=management_state.plan.project_name,
        progress=progress,
        task_delays=task_delays,
        schedule_impact=(
            schedule_impact.model_dump(mode="json")
            if schedule_impact
            else None
        ),
        revised_completion_week=revised_completion_week,
        task_statuses={
            record.task_id: record.status
            for record in progress_records
        },
        recommendations=recommendations,
    )
