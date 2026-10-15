
from pydantic import BaseModel, Field, model_validator

from schemas.project_plan import ProjectPlan
from schemas.work_schedule import WorkSchedule


class TaskScheduleImpact(BaseModel):
    task_id: int
    original_start_week: int = Field(ge=1)
    original_completion_week: int = Field(ge=1)
    revised_start_week: int = Field(ge=1)
    revised_completion_week: int = Field(ge=1)
    delayed: bool = False

    @model_validator(mode="after")
    def validate_week_ranges(self):
        if self.original_completion_week < self.original_start_week:
            raise ValueError("Original completion cannot precede start")

        if self.revised_completion_week < self.revised_start_week:
            raise ValueError("Revised completion cannot precede start")

        return self


class ScheduleImpactReport(BaseModel):
    project_name: str
    original_project_completion_week: int = Field(ge=1)
    revised_project_completion_week: int = Field(ge=1)
    project_delay_weeks: int = Field(ge=0)
    affected_tasks: list[TaskScheduleImpact] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def calculate_schedule_impact(
    plan: ProjectPlan,
    schedule: WorkSchedule,
    delayed_task_id: int,
    delay_weeks: int,
) -> ScheduleImpactReport:
    """Estimate delay impact for the dependency-valid, scheduled subset."""

    if delay_weeks < 0:
        raise ValueError("delay_weeks cannot be negative")

    plan_tasks = {task.task_id: task for task in plan.tasks}
    scheduled_tasks = {
        task.task_id: task for task in schedule.scheduled_tasks
    }

    if delayed_task_id not in plan_tasks:
        raise ValueError(f"Unknown task ID: {delayed_task_id}")

    if delayed_task_id not in scheduled_tasks:
        raise ValueError(
            f"Task {delayed_task_id} is not present in the work schedule"
        )

    missing_tasks = sorted(set(plan_tasks) - set(scheduled_tasks))

    # Exclude scheduled tasks whose dependencies, directly or indirectly,
    # cannot be analyzed because they are not scheduled.
    analyzable_ids = set(scheduled_tasks)
    changed = True

    while changed:
        changed = False

        for task_id in list(analyzable_ids):
            dependencies = plan_tasks[task_id].dependencies

            if any(dep_id not in analyzable_ids for dep_id in dependencies):
                analyzable_ids.remove(task_id)
                changed = True

    if delayed_task_id not in analyzable_ids:
        raise ValueError(
            f"Task {delayed_task_id} cannot be analyzed because "
            "one or more of its dependencies are unscheduled."
        )

    # Validate dependencies for tasks that can be analyzed.
        # Validate dependencies only within the analyzable subset.
    for task_id in analyzable_ids:
        task = plan_tasks[task_id]
        scheduled = scheduled_tasks[task_id]

        for dependency_id in task.dependencies:
            if dependency_id not in analyzable_ids:
                continue

            dependency = scheduled_tasks[dependency_id]

            if scheduled.start_week <= dependency.completion_week:
                raise ValueError(
                    f"Schedule violates dependency {dependency_id} "
                    f"for task {task_id}"
                )
    original_completion = max(
        scheduled_tasks[task_id].completion_week
        for task_id in analyzable_ids
    )

    revised_start = {
        task_id: scheduled_tasks[task_id].start_week
        for task_id in analyzable_ids
    }
    revised_completion = {
        task_id: scheduled_tasks[task_id].completion_week
        for task_id in analyzable_ids
    }

    revised_completion[delayed_task_id] += delay_weeks

    # Process only tasks whose dependencies are analyzable.
    pending = set(analyzable_ids)
    processed = set()

    while pending:
        ready = sorted(
            task_id
            for task_id in pending
            if all(
                dep_id in processed
                for dep_id in plan_tasks[task_id].dependencies
            )
        )

        if not ready:
            raise ValueError("Unable to order tasks by dependencies")

        for task_id in ready:
            task = plan_tasks[task_id]

            if task_id != delayed_task_id and task.dependencies:
                earliest_start = max(
                    revised_completion[dep_id] + 1
                    for dep_id in task.dependencies
                )

                if revised_start[task_id] < earliest_start:
                    duration = (
                        revised_completion[task_id]
                        - revised_start[task_id]
                        + 1
                    )

                    revised_start[task_id] = earliest_start
                    revised_completion[task_id] = (
                        earliest_start + duration - 1
                    )

            processed.add(task_id)
            pending.remove(task_id)

    revised_project_completion = max(revised_completion.values())
    impacts = []

    for task_id in sorted(analyzable_ids):
        original = scheduled_tasks[task_id]

        if (
            revised_start[task_id] != original.start_week
            or revised_completion[task_id] != original.completion_week
        ):
            impacts.append(
                TaskScheduleImpact(
                    task_id=task_id,
                    original_start_week=original.start_week,
                    original_completion_week=original.completion_week,
                    revised_start_week=revised_start[task_id],
                    revised_completion_week=revised_completion[task_id],
                    delayed=True,
                )
            )

    notes = [
        f"Delay applied to task {delayed_task_id}: {delay_weeks} week(s).",
        "Dependency delays are propagated through analyzable tasks.",
        "Employee capacity and resource conflicts are not re-optimized.",
    ]

    if missing_tasks:
        notes.append(
            f"Unscheduled tasks excluded from impact analysis: {missing_tasks}."
        )

    excluded_scheduled = sorted(set(scheduled_tasks) - analyzable_ids)

    if excluded_scheduled:
        notes.append(
            "Scheduled tasks excluded because their dependency chains "
            f"contain unscheduled tasks: {excluded_scheduled}."
        )

    notes.append(
        "Project completion reflects only the analyzable scheduled subset, "
        "not necessarily the complete project."
    )

    return ScheduleImpactReport(
        project_name=plan.project_name,
        original_project_completion_week=original_completion,
        revised_project_completion_week=revised_project_completion,
        project_delay_weeks=max(
            0,
            revised_project_completion - original_completion,
        ),
        affected_tasks=impacts,
        notes=notes,
    )
