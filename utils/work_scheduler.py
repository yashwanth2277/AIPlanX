
from schemas.employee import Employee
from schemas.project_plan import ProjectPlan
from schemas.work_schedule import (
    ScheduledTask,
    WeeklyAllocation,
    WorkSchedule,
)
from utils.skill_matcher import calculate_skill_match


def build_work_schedule(
    plan: ProjectPlan,
    employees: list[Employee],
    assignments=None,
) -> WorkSchedule:
    schedule = WorkSchedule()

    # Week 1 accounts for existing workload.
    remaining_capacity = {
        employee.employee_id: {
            1: round(
                employee.weekly_capacity_hours
                * (1 - employee.current_workload_percent / 100),
                2,
            )
        }
        for employee in employees
    }

    scheduled_by_task = {}
    pending_tasks = list(plan.tasks)

    while pending_tasks:
        ready_tasks = [
            task
            for task in pending_tasks
            if all(
                dependency_id in scheduled_by_task
                for dependency_id in task.dependencies
            )
        ]

        if not ready_tasks:
            for task in pending_tasks:
                blocked = [
                    dependency_id
                    for dependency_id in task.dependencies
                    if dependency_id not in scheduled_by_task
                ]
                schedule.unscheduled_tasks.append({
                    "task_id": task.task_id,
                    "task_title": task.title,
                    "reason": (
                        f"Blocked by unscheduled prerequisite(s): {blocked}."
                    ),
                })
            break

        ready_tasks.sort(
            key=lambda task: (
                task.priority == "High",
                len(task.dependencies),
            ),
            reverse=True,
        )

        for task in ready_tasks:
            candidates = []

            for employee in employees:
                skill_match = calculate_skill_match(task, employee)
                if skill_match < 0.5:
                    continue

                score = (
                    0.65 * skill_match
                    + 0.25 * (
                        1 - employee.current_workload_percent / 100
                    )
                    + 0.10 * min(employee.experience, 7) / 35
                )
                candidates.append((score, skill_match, employee))

            candidates.sort(
                key=lambda item: item[0],
                reverse=True,
            )

            dependency_completion = max(
                (
                    scheduled_by_task[dep].completion_week
                    for dep in task.dependencies
                ),
                default=1,
            )

            selected = None

            for score, skill_match, employee in candidates:
                week = dependency_completion
                hours_left = task.estimated_hours
                allocations = []

                # Simulate allocation first. Do not reserve capacity
                # unless the complete task can be scheduled.
                while hours_left > 0:
                    if week not in remaining_capacity[employee.employee_id]:
                        remaining_capacity[employee.employee_id][week] = (
                            employee.weekly_capacity_hours
                        )

                    available = remaining_capacity[
                        employee.employee_id
                    ][week]

                    if available > 0:
                        allocated = min(hours_left, available)
                        allocated = round(allocated, 2)

                        if allocated > 0:
                            allocations.append(
                                WeeklyAllocation(
                                    week=week,
                                    allocated_hours=allocated,
                                )
                            )
                            hours_left = round(
                                hours_left - allocated, 2
                            )

                    if hours_left > 0:
                        week += 1

                if allocations and hours_left == 0:
                    selected = (
                        score,
                        skill_match,
                        employee,
                        allocations,
                    )
                    break

            if selected is None:
                schedule.unscheduled_tasks.append({
                    "task_id": task.task_id,
                    "task_title": task.title,
                    "reason": (
                        "No employee meets the skill-match threshold "
                        "and has schedulable weekly capacity."
                    ),
                })
                pending_tasks.remove(task)
                continue

            score, skill_match, employee, allocations = selected

            # Commit the allocation only after the whole task fits.
            for allocation in allocations:
                remaining_capacity[employee.employee_id][
                    allocation.week
                ] = round(
                    remaining_capacity[employee.employee_id][
                        allocation.week
                    ] - allocation.allocated_hours,
                    2,
                )

            required = {
                skill.strip().casefold()
                for skill in task.required_skills
                if skill.strip()
            }
            actual = {
                skill.strip().casefold()
                for skill in employee.skills
                if skill.strip()
            }
            matched = sorted(required & actual)
            missing = sorted(required - actual)

            scheduled = ScheduledTask(
                task_id=task.task_id,
                task_title=task.title,
                employee_id=employee.employee_id,
                employee_name=employee.employee_name,
                total_estimated_hours=task.estimated_hours,
                weekly_allocations=allocations,
                start_week=allocations[0].week,
                completion_week=allocations[-1].week,
                assignment_reason=(
                    f"Matched skills: {', '.join(matched) or 'None'}. "
                    f"Missing skills: {', '.join(missing) or 'None'}. "
                    f"Skill match: {skill_match:.0%}. "
                    f"Scheduled over {len(allocations)} week(s)."
                ),
            )

            schedule.scheduled_tasks.append(scheduled)
            scheduled_by_task[task.task_id] = scheduled
            pending_tasks.remove(task)

    return schedule
