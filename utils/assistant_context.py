
from pathlib import Path
from typing import Any

from schemas.employee import Employee
from schemas.final_report import FinalProjectReport
from schemas.project_management import ProjectManagementState
from schemas.work_schedule import WorkSchedule
from utils.employee_parser import parse_employee_csv
from utils.management_persistence import load_management_state
from utils.schedule_persistence import load_work_schedule


def build_assistant_context_from_state(
    session_name: str,
    *,
    report: FinalProjectReport,
    management_state: ProjectManagementState,
    work_schedule: WorkSchedule,
    employees: list[Employee],
) -> dict[str, Any]:
    """Build read-only assistant context from in-memory project data."""

    plan = management_state.plan
    progress_by_id = {
        progress.task_id: progress
        for progress in management_state.task_progress
    }
    assignments_by_id = {
        assignment.task_id: assignment
        for assignment in management_state.assignments
    }

    tasks = []
    for task in plan.tasks:
        progress = progress_by_id[task.task_id]
        assignment = assignments_by_id.get(task.task_id)

        tasks.append({
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "required_skills": task.required_skills,
            "estimated_hours": task.estimated_hours,
            "priority": task.priority,
            "dependencies": task.dependencies,
            "status": progress.status.value,
            "progress_percent": progress.progress_percent,
            "actual_hours_spent": progress.actual_hours_spent,
            "delays": [
                delay.model_dump(mode="json")
                for delay in progress.delays
            ],
            "assigned_employee_id": (
                assignment.employee_id if assignment else None
            ),
        })

    return {
        "session_name": session_name,
        "project": {
            "name": plan.project_name,
            "summary": plan.project_summary,
            "total_estimated_hours": plan.total_estimated_hours,
            "risks": plan.risks,
            "original_report": report.model_dump(mode="json"),
        },
        "tasks": tasks,
        "schedule": work_schedule.model_dump(mode="json"),
        "employees": [
            employee.model_dump(mode="json")
            for employee in employees
        ],
        "assignment_changes": [
            change.model_dump(mode="json")
            for change in management_state.assignment_changes
        ],
    }


def build_assistant_context(
    session_name: str,
    report_path: str | Path = "final_report.json",
    employee_path: str | Path = "employees.csv",
    session_dir: str | Path = "management_sessions",
) -> dict[str, Any]:
    """Build read-only project context for the AI Project Assistant."""

    if (
        not session_name
        or session_name in {".", ".."}
        or any(
            char not in
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for char in session_name
        )
    ):
        raise ValueError(
            "Session name must contain only letters, numbers, "
            "underscores, and hyphens."
        )

    session_path = Path(session_dir) / session_name
    state_path = session_path / "management_state.json"
    schedule_path = session_path / "work_schedule.json"

    report_file = Path(report_path)
    if not report_file.is_file():
        raise FileNotFoundError(
            f"Project report not found: {report_file}"
        )

    report = FinalProjectReport.model_validate_json(
        report_file.read_text(encoding="utf-8")
    )
    management_state = load_management_state(state_path)
    work_schedule = load_work_schedule(schedule_path)
    roster = parse_employee_csv(employee_path)

    return build_assistant_context_from_state(
        session_name,
        report=report,
        management_state=management_state,
        work_schedule=work_schedule,
        employees=roster.employees,
    )
