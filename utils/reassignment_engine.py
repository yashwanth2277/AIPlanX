from schemas.assignment import TaskAssignment
from schemas.employee import EmployeeRoster
from schemas.project_management import (
    AssignmentChange,
    ProjectManagementState,
)
from utils.skill_matcher import check_skill_match_details


def reassign_task(
    state: ProjectManagementState,
    roster: EmployeeRoster,
    task_id: int,
    new_employee_id: str,
    reason: str,
    previous_employee_id: str | None = None,
) -> ProjectManagementState:
    """Reassign a task after validating skills (>= 50% match) and available capacity."""

    plan_tasks = {
        task.task_id: task
        for task in state.plan.tasks
    }

    if task_id not in plan_tasks:
        raise ValueError(f"Unknown task ID: {task_id}")

    if not reason.strip() or len(reason.strip()) < 3:
        raise ValueError(
            "Reassignment reason must contain at least 3 characters"
        )

    employees = {
        employee.employee_id: employee
        for employee in roster.employees
    }

    if new_employee_id not in employees:
        raise ValueError(f"Unknown employee ID: {new_employee_id}")

    if previous_employee_id:
        current_assignment = next(
            (
                assignment
                for assignment in state.assignments
                if assignment.task_id == task_id
                and assignment.employee_id == previous_employee_id
            ),
            None,
        )
    else:
        current_assignment = next(
            (
                assignment
                for assignment in state.assignments
                if assignment.task_id == task_id
            ),
            None,
        )

    if current_assignment is None:
        raise ValueError(f"Task {task_id} has no current assignment")

    if current_assignment.employee_id == new_employee_id:
        raise ValueError("Task is already assigned to this employee")

    # If the task already has other collaborators, ensure new_employee is not already assigned
    already_assigned = any(
        a.task_id == task_id and a.employee_id == new_employee_id
        for a in state.assignments
    )
    if already_assigned:
        raise ValueError("Task is already assigned to this employee")

    new_employee = employees[new_employee_id]
    task = plan_tasks[task_id]

    # Validate skills deterministically: candidate qualifies if matching >= 50% of required skills
    qualifies, ratio, matched, required = check_skill_match_details(
        candidate_skills=new_employee.skills,
        task_required_skills=task.required_skills,
    )

    if not qualifies:
        raise ValueError(
            "Employee lacks required skills: "
            f"candidate matches {len(matched)} of {len(required)} "
            f"required skills ({ratio*100:.0f}%); at least 50% match is required"
        )

    # Check remaining weekly capacity using the employee's current workload.
    available_hours = (
        new_employee.weekly_capacity_hours
        * (1 - new_employee.current_workload_percent / 100)
    )

    if task.estimated_hours > available_hours:
        raise ValueError(
            f"Insufficient weekly capacity: task requires "
            f"{task.estimated_hours} hours, but employee has "
            f"{available_hours:.2f} hours available"
        )

    match_score = max(0.01, min(1.0, round(ratio, 2))) if ratio is not None else 1.0

    updated_assignment = TaskAssignment(
        task_id=current_assignment.task_id,
        task_title=current_assignment.task_title,
        employee_id=new_employee.employee_id,
        employee_name=new_employee.employee_name,
        match_score=match_score,
        assignment_reason=f"Reassigned: {reason.strip()}",
    )

    change = AssignmentChange(
        task_id=task_id,
        previous_employee_id=current_assignment.employee_id,
        new_employee_id=new_employee.employee_id,
        reason=reason.strip(),
    )

    updated_assignments = [
        updated_assignment
        if (
            item.task_id == task_id
            and item.employee_id == current_assignment.employee_id
        )
        else item
        for item in state.assignments
    ]

    return ProjectManagementState(
        plan=state.plan,
        task_progress=state.task_progress,
        assignments=updated_assignments,
        assignment_changes=[
            *state.assignment_changes,
            change,
        ],
        applied_delay_ids=state.applied_delay_ids,
        activity_history=state.activity_history,
    )


def add_collaborator(
    state: ProjectManagementState,
    roster: EmployeeRoster,
    task_id: int,
    employee_id: str,
    reason: str = "Collaborator added",
) -> ProjectManagementState:
    """Add a collaborator to a task without replacing existing assignees."""

    plan_tasks = {
        task.task_id: task
        for task in state.plan.tasks
    }

    if task_id not in plan_tasks:
        raise ValueError(f"Unknown task ID: {task_id}")

    if not reason.strip() or len(reason.strip()) < 3:
        raise ValueError(
            "Reason must contain at least 3 characters"
        )

    employees = {
        employee.employee_id: employee
        for employee in roster.employees
    }

    if employee_id not in employees:
        raise ValueError(f"Unknown employee ID: {employee_id}")

    already_assigned = any(
        a.task_id == task_id and a.employee_id == employee_id
        for a in state.assignments
    )
    if already_assigned:
        raise ValueError("Employee is already assigned to this task")

    new_employee = employees[employee_id]
    task = plan_tasks[task_id]

    qualifies, ratio, matched, required = check_skill_match_details(
        candidate_skills=new_employee.skills,
        task_required_skills=task.required_skills,
    )

    if not qualifies:
        raise ValueError(
            "Employee lacks required skills: "
            f"candidate matches {len(matched)} of {len(required)} "
            f"required skills ({ratio*100:.0f}%); at least 50% match is required"
        )

    match_score = max(0.01, min(1.0, round(ratio, 2))) if ratio is not None else 1.0

    new_assignment = TaskAssignment(
        task_id=task.task_id,
        task_title=task.title,
        employee_id=new_employee.employee_id,
        employee_name=new_employee.employee_name,
        match_score=match_score,
        assignment_reason=f"Collaborator added: {reason.strip()}",
    )

    change = AssignmentChange(
        task_id=task_id,
        previous_employee_id=None,
        new_employee_id=new_employee.employee_id,
        reason=f"Collaborator added: {reason.strip()}",
    )

    return ProjectManagementState(
        plan=state.plan,
        task_progress=state.task_progress,
        assignments=[*state.assignments, new_assignment],
        assignment_changes=[
            *state.assignment_changes,
            change,
        ],
        applied_delay_ids=state.applied_delay_ids,
        activity_history=state.activity_history,
    )


def remove_collaborator(
    state: ProjectManagementState,
    task_id: int,
    employee_id: str,
    reason: str = "Collaborator removed",
) -> ProjectManagementState:
    """Remove a collaborator from a task, preserving remaining assignees."""

    plan_tasks = {
        task.task_id: task
        for task in state.plan.tasks
    }

    if task_id not in plan_tasks:
        raise ValueError(f"Unknown task ID: {task_id}")

    if not reason.strip() or len(reason.strip()) < 3:
        raise ValueError(
            "Reason must contain at least 3 characters"
        )

    existing_assignment = next(
        (
            a for a in state.assignments
            if a.task_id == task_id and a.employee_id == employee_id
        ),
        None,
    )
    if existing_assignment is None:
        raise ValueError(f"Employee {employee_id} is not assigned to task {task_id}")

    updated_assignments = [
        a for a in state.assignments
        if not (a.task_id == task_id and a.employee_id == employee_id)
    ]

    remaining = [a for a in updated_assignments if a.task_id == task_id]
    next_id = remaining[0].employee_id if remaining else "unassigned"

    change = AssignmentChange(
        task_id=task_id,
        previous_employee_id=employee_id,
        new_employee_id=next_id,
        reason=f"Collaborator removed: {reason.strip()}",
    )

    return ProjectManagementState(
        plan=state.plan,
        task_progress=state.task_progress,
        assignments=updated_assignments,
        assignment_changes=[
            *state.assignment_changes,
            change,
        ],
        applied_delay_ids=state.applied_delay_ids,
        activity_history=state.activity_history,
    )
