
from schemas.employee import Employee
from schemas.project_plan import ProjectPlan
from schemas.work_schedule import (
    ScheduledTask,
    WeeklyAllocation,
    WorkSchedule,
)


def reschedule_work_schedule(
    plan: ProjectPlan,
    employees: list[Employee],
    schedule: WorkSchedule,
    delayed_task_id: int,
    delay_weeks: int,
) -> WorkSchedule:
    """Reschedule scheduled tasks while preserving unscheduled tasks."""

    if delay_weeks < 0:
        raise ValueError("delay_weeks cannot be negative")

    employee_ids = [employee.employee_id for employee in employees]
    if len(set(employee_ids)) != len(employee_ids):
        raise ValueError("Employee IDs must be unique")

    plan_tasks = {task.task_id: task for task in plan.tasks}
    original_tasks = {
        task.task_id: task for task in schedule.scheduled_tasks
    }
    employee_by_id = {
        employee.employee_id: employee for employee in employees
    }

    if delayed_task_id not in plan_tasks:
        raise ValueError(f"Unknown task ID: {delayed_task_id}")

    if delayed_task_id not in original_tasks:
        raise ValueError(f"Task {delayed_task_id} is not scheduled")

    unknown_task_ids = set(original_tasks) - set(plan_tasks)
    if unknown_task_ids:
        raise ValueError(
            f"Schedule contains unknown task IDs: {sorted(unknown_task_ids)}"
        )

    unknown_employees = {
        task.employee_id
        for task in original_tasks.values()
        if task.employee_id not in employee_by_id
    }
    if unknown_employees:
        raise ValueError(
            f"Unknown assigned employees: {sorted(unknown_employees)}"
        )

    scheduled_ids = set(original_tasks)
    unscheduled_ids = set(plan_tasks) - scheduled_ids

    # A scheduled task cannot be safely rescheduled if any of its
    # dependencies are not scheduled.
    for task_id in scheduled_ids:
        missing_dependencies = (
            set(plan_tasks[task_id].dependencies) - scheduled_ids
        )
        if missing_dependencies:
            raise ValueError(
                f"Cannot safely reschedule task {task_id}: "
                f"dependencies are unscheduled "
                f"{sorted(missing_dependencies)}"
            )

    # Reserve capacity for tasks that are unscheduled in the plan but
    # still represented by explicit unscheduled records is unnecessary;
    # only actual scheduled tasks consume employee capacity.
    remaining_capacity: dict[str, dict[int, float]] = {}

    for employee in employees:
        remaining_capacity[employee.employee_id] = {
            1: round(
                employee.weekly_capacity_hours
                * (1 - employee.current_workload_percent / 100),
                2,
            )
        }

    revised_by_task: dict[int, ScheduledTask] = {}
    pending = set(scheduled_ids)
    processed: set[int] = set()

    while pending:
        ready = sorted(
            (
                task_id
                for task_id in pending
                if all(
                    dependency_id in processed
                    for dependency_id in plan_tasks[task_id].dependencies
                )
            ),
            key=lambda task_id: (
                original_tasks[task_id].start_week,
                task_id,
            ),
        )

        if not ready:
            raise ValueError(
                "Unable to order scheduled tasks by dependencies"
            )

        for task_id in ready:
            task = plan_tasks[task_id]
            original = original_tasks[task_id]
            employee = employee_by_id[original.employee_id]

            earliest_week = original.start_week

            if task.dependencies:
                dependency_week = max(
                    revised_by_task[dependency_id].completion_week + 1
                    for dependency_id in task.dependencies
                )
                earliest_week = max(earliest_week, dependency_week)

            if task_id == delayed_task_id:
                earliest_week += delay_weeks

            week = earliest_week
            hours_left = task.estimated_hours
            allocations = []

            simulated_capacity = dict(
                remaining_capacity[employee.employee_id]
            )

            while hours_left > 0:
                if week not in simulated_capacity:
                    simulated_capacity[week] = (
                        employee.weekly_capacity_hours
                    )

                available = simulated_capacity[week]

                if available > 0:
                    allocated = round(min(hours_left, available), 2)

                    if allocated > 0:
                        allocations.append(
                            WeeklyAllocation(
                                week=week,
                                allocated_hours=allocated,
                            )
                        )

                        simulated_capacity[week] = round(
                            available - allocated, 2
                        )
                        hours_left = round(hours_left - allocated, 2)

                if hours_left > 0:
                    week += 1

            remaining_capacity[employee.employee_id] = simulated_capacity

            revised_by_task[task_id] = ScheduledTask(
                task_id=task_id,
                task_title=original.task_title,
                employee_id=employee.employee_id,
                employee_name=employee.employee_name,
                total_estimated_hours=task.estimated_hours,
                weekly_allocations=allocations,
                start_week=allocations[0].week,
                completion_week=allocations[-1].week,
                assignment_reason=original.assignment_reason,
            )

            processed.add(task_id)
            pending.remove(task_id)

    return WorkSchedule(
        scheduled_tasks=[
            revised_by_task[task.task_id]
            for task in schedule.scheduled_tasks
        ],
        unscheduled_tasks=[
            *schedule.unscheduled_tasks,
            *[
                {
                    "task_id": task_id,
                    "reason": "Task was not present in the original schedule; "
                    "retained as unscheduled during rescheduling.",
                }
                for task_id in sorted(unscheduled_ids)
                if not any(
                    item.get("task_id") == task_id
                    for item in schedule.unscheduled_tasks
                )
            ],
        ],
    )
