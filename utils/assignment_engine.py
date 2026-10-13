
from asyncio import current_task

from schemas.assignment import (
    AssignmentReport,
    TaskAssignment,
    UnassignedTask,
)
from schemas.employee import Employee
from schemas.project_plan import ProjectPlan
from utils.skill_matcher import calculate_skill_match


def assign_tasks(
    plan: ProjectPlan,
    employees: list[Employee],
) -> AssignmentReport:
    report = AssignmentReport()

    remaining_hours = {
        employee.employee_id: (
            employee.weekly_capacity_hours
            * (1 - employee.current_workload_percent / 100)
        )
        for employee in employees
    }

    assigned_task_ids = set()
    pending_tasks = list(plan.tasks)
    unassigned_reasons = {}

    while pending_tasks:
        ready_tasks = [
            current_task
            for current_task in pending_tasks
            if all(
                dependency_id in assigned_task_ids
                for dependency_id in current_task.dependencies
            )
        ]

        # If no task is ready, mark the remaining tasks as blocked.
        if not ready_tasks:
            for current_task in pending_tasks:
                blocked_dependencies = [
                    dependency_id
                    for dependency_id in current_task.dependencies
                    if dependency_id not in assigned_task_ids
                ]

                report.unassigned_tasks.append(
                    UnassignedTask(
                        task_id=current_task.task_id,
                        task_title=current_task.title,
                        reason=(
                            "Blocked because prerequisite task(s) "
                            f"{blocked_dependencies} were not assigned."
                        ),
                    )
                )
            break

        ready_tasks.sort(
            key=lambda current_task: (
                len(current_task.dependencies),
                current_task.priority == "High",
            ),
            reverse=True,
        )

        for current_task in ready_tasks:
            ranked = []

            for employee in employees:
                available = remaining_hours[employee.employee_id]

# Preserve the existing single-week capacity constraint.
                if current_task.estimated_hours > available:
                    continue
                skill_match = calculate_skill_match(
                    current_task, employee
                )

                if skill_match < 0.5:
                    continue

                score = (
                    0.65 * skill_match
                    + 0.25
                    * (1 - employee.current_workload_percent / 100)
                    + 0.10 * min(employee.experience, 7) / 35
                )

                ranked.append((score, skill_match, employee))

            if not ranked:
                unassigned_reasons[current_task.task_id] = (
                    "No employee meets the minimum skill-match "
                    "threshold and remaining weekly capacity."
                )
                pending_tasks.remove(current_task)
                continue

            ranked.sort(key=lambda item: item[0], reverse=True)
            score, skill_match, employee = ranked[0]

            required_skills = {
                skill.strip().casefold()
                for skill in current_task.required_skills
                if skill.strip()
            }
            employee_skills = {
                skill.strip().casefold()
                for skill in employee.skills
                if skill.strip()
            }

            matched_skills = sorted(required_skills & employee_skills)
            missing_skills = sorted(required_skills - employee_skills)

            report.assignments.append(
                TaskAssignment(
                    task_id=current_task.task_id,
                    task_title=current_task.title,
                    employee_id=employee.employee_id,
                    employee_name=employee.employee_name,
                    match_score=round(score, 3),
                    assignment_reason=(
                        f"Matched skills: "
                        f"{', '.join(matched_skills) or 'None'}. "
                        f"Missing skills: "
                        f"{', '.join(missing_skills) or 'None'}. "
                        f"Skill match: {skill_match:.0%}. "
                        f"Allocated {current_task.estimated_hours} hours."
                    ),
                )
            )

            remaining_hours[employee.employee_id] -= (
                current_task.estimated_hours
            )
            assigned_task_ids.add(current_task.task_id)
            pending_tasks.remove(current_task)

    # Report tasks rejected for skill or capacity reasons.
    for current_task in plan.tasks:
        if current_task.task_id in unassigned_reasons:
            report.unassigned_tasks.append(
                UnassignedTask(
                    task_id=current_task.task_id,
                    task_title=current_task.title,
                    reason=unassigned_reasons[current_task.task_id],
                )
            )

    # Explain tasks that depend on tasks which were not assigned.
    already_reported = {
        item.task_id for item in report.unassigned_tasks
    }

    for current_task in plan.tasks:
        if (
            current_task.task_id not in assigned_task_ids
            and current_task.task_id not in already_reported
        ):
            blocked_dependencies = [
                dependency_id
                for dependency_id in current_task.dependencies
                if dependency_id not in assigned_task_ids
            ]

            report.unassigned_tasks.append(
                UnassignedTask(
                    task_id=current_task.task_id,
                    task_title=current_task.title,
                    reason=(
                        "Blocked because prerequisite task(s) "
                        f"{blocked_dependencies} were not assigned."
                    ),
                )
            )

    return report
