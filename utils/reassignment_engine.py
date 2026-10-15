
from schemas.assignment import TaskAssignment
from schemas.employee import EmployeeRoster
from schemas.project_management import (
    AssignmentChange,
    ProjectManagementState,
)


def reassign_task(
    state: ProjectManagementState,
    roster: EmployeeRoster,
    task_id: int,
    new_employee_id: str,
    reason: str,
) -> ProjectManagementState:
    """Reassign a task after validating skills and available capacity."""

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

    new_employee = employees[new_employee_id]
    task = plan_tasks[task_id]

    # Validate required skills, ignoring case and surrounding whitespace.
    required_skills = {
        skill.strip().casefold()
        for skill in task.required_skills
        if skill.strip()
    }
    employee_skills = {
        skill.strip().casefold()
        for skill in new_employee.skills
        if skill.strip()
    }

    missing_skills = required_skills - employee_skills

    if missing_skills:
        raise ValueError(
            "Employee lacks required skills: "
            + ", ".join(sorted(missing_skills))
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

    # Reconstruct the model to apply Pydantic validation.
    updated_assignment = TaskAssignment(
        task_id=current_assignment.task_id,
        task_title=current_assignment.task_title,
        employee_id=new_employee.employee_id,
        employee_name=new_employee.employee_name,
        match_score=current_assignment.match_score,
        assignment_reason=f"Reassigned: {reason.strip()}",
    )

    change = AssignmentChange(
        task_id=task_id,
        previous_employee_id=current_assignment.employee_id,
        new_employee_id=new_employee.employee_id,
        reason=reason.strip(),
    )

    updated_assignments = [
        updated_assignment if item.task_id == task_id else item
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
    )
