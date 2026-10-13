
from datetime import date

from schemas.project_plan import ProjectPlan
from schemas.progress_tracking import ProgressReport


def track_project_progress(
    plan: ProjectPlan,
    completed_task_ids: list[int],
    actual_hours: dict[int, float],
    blocked_tasks: dict[int, list[str]] | None = None,
) -> ProgressReport:
    blocked_tasks = blocked_tasks or {}

    plan_task_ids = {task.task_id for task in plan.tasks}
    unknown_ids = set(completed_task_ids) - plan_task_ids
    unknown_ids |= set(actual_hours) - plan_task_ids
    unknown_ids |= set(blocked_tasks) - plan_task_ids

    if unknown_ids:
        raise ValueError(f"Unknown task IDs: {sorted(unknown_ids)}")

    completed_ids = set(completed_task_ids)
    task_progress = []
    delayed_task_ids = []

    for task in plan.tasks:
        is_completed = task.task_id in completed_ids
        hours = actual_hours.get(task.task_id, 0.0)
        blockers = blocked_tasks.get(task.task_id, [])

        status = (
            "Completed" if is_completed
            else "Blocked" if blockers
            else "In Progress" if hours > 0
            else "Pending"
        )

        percentage = 100.0 if is_completed else (
            min(99.0, hours / task.estimated_hours * 100)
            if hours > 0 else 0.0
        )

        if not is_completed and hours > task.estimated_hours:
            delayed_task_ids.append(task.task_id)

        task_progress.append({
            "task_id": task.task_id,
            "task_title": task.title,
            "planned_hours": task.estimated_hours,
            "actual_hours": hours,
            "status": status,
            "progress_percentage": percentage,
            "blockers": blockers,
        })

    completed_count = len(completed_ids)
    pending_count = len(plan.tasks) - completed_count
    overall_progress = sum(
        item["progress_percentage"] for item in task_progress
    ) / len(task_progress)

    recommendations = []
    if delayed_task_ids:
        recommendations.append(
            "Review tasks whose actual hours exceed their planned estimates."
        )
    if blocked_tasks:
        recommendations.append(
            "Resolve blockers and review affected task dependencies."
        )
    if not recommendations:
        recommendations.append(
            "Continue updating task status and actual hours regularly."
        )

    return ProgressReport(
        project_name=plan.project_name,
        overall_progress_percentage=round(overall_progress, 2),
        completed_tasks=completed_count,
        pending_tasks=pending_count,
        delayed_tasks=delayed_task_ids,
        task_progress=task_progress,
        recommendations=recommendations,
    )


if __name__ == "__main__":
    sample_plan = ProjectPlan(
        project_name="Student Task Manager",
        project_summary="A task management app built with Python.",
        total_estimated_hours=12,
        tasks=[
            {
                "task_id": 1,
                "title": "Design database",
                "description": "Design the task database.",
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Build API",
                "description": "Implement task management endpoints.",
                "estimated_hours": 8,
                "priority": "High",
                "dependencies": [1],
            },
        ],
    )

    report = track_project_progress(
        plan=sample_plan,
        completed_task_ids=[1],
        actual_hours={1: 3, 2: 2},
        blocked_tasks={},
    )

    print(report.model_dump_json(indent=2))
