
import json
from pathlib import Path

from schemas.final_report import FinalProjectReport
from schemas.project_management import ProjectManagementState
from schemas.work_schedule import WorkSchedule

from agents.management_workflow import build_management_workflow

from utils.assignment_engine import assign_tasks
from utils.employee_parser import parse_employee_csv
from utils.management_initializer import initialize_management_state
from utils.management_persistence import (
    load_management_state,
    save_management_state,
)
from utils.work_scheduler import build_work_schedule
from utils.schedule_persistence import (
    load_work_schedule,
    save_work_schedule,
)


REPORT_PATH = Path("final_report.json")
EMPLOYEE_PATH = Path("employees.csv")
SESSION_DIR = Path("management_sessions")


def session_paths(session_name: str) -> tuple[Path, Path]:
    """Return persistence paths for a session with a safe name."""

    if (
        not session_name
        or session_name in {".", ".."}
        or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in session_name)
    ):
        raise ValueError(
            "Session name must contain only letters, numbers, "
            "underscores, and hyphens."
        )

    session_dir = SESSION_DIR / session_name
    return (
        session_dir / "management_state.json",
        session_dir / "work_schedule.json",
    )


def create_session(session_name: str):
    """Create a new session from the existing final project report."""

    state_path, schedule_path = session_paths(session_name)

    if state_path.exists() or schedule_path.exists():
        raise FileExistsError(
            f"Session '{session_name}' already exists. "
            "Resume it instead of overwriting it."
        )

    if not REPORT_PATH.is_file():
        raise FileNotFoundError(
            "final_report.json not found. Run run_project.py first."
        )

    report = FinalProjectReport.model_validate_json(
        REPORT_PATH.read_text(encoding="utf-8")
    )

    roster = parse_employee_csv(EMPLOYEE_PATH)
    employees = roster.employees

    assignment_report = assign_tasks(
        plan=report.project_plan,
        employees=employees,
    )

    management_state = initialize_management_state(
        plan=report.project_plan,
        assignments=assignment_report.assignments,
    )

    work_schedule = build_work_schedule(
        plan=report.project_plan,
        employees=employees,
        assignments=assignment_report.assignments,
    )

    save_management_state(management_state, state_path)
    save_work_schedule(work_schedule, schedule_path)

    print(f"\nCreated management session: {session_name}")
    print(f"Project: {report.project_plan.project_name}")
    print(f"Tasks: {len(report.project_plan.tasks)}")
    print(f"Assigned tasks: {len(assignment_report.assignments)}")
    print(f"Unassigned tasks: {len(assignment_report.unassigned_tasks)}")
    print(f"Scheduled tasks: {len(work_schedule.scheduled_tasks)}")
    print(f"State saved to: {state_path}")
    print(f"Schedule saved to: {schedule_path}")

    return management_state, work_schedule, employees


def resume_session(session_name: str):
    """Load an existing session without resetting progress."""

    state_path, schedule_path = session_paths(session_name)

    management_state = load_management_state(state_path)
    work_schedule = load_work_schedule(schedule_path)

    roster = parse_employee_csv(EMPLOYEE_PATH)

    print(f"\nResumed management session: {session_name}")
    print(f"Project: {management_state.plan.project_name}")
    print(f"Tasks: {len(management_state.plan.tasks)}")
    print("Saved progress and schedule restored.")

    return management_state, work_schedule, roster.employees


def show_progress(state: ProjectManagementState) -> None:
    """Display the current status of every task."""

    progress_by_id = {
        item.task_id: item for item in state.task_progress
    }

    print("\n========== TASK PROGRESS ==========")

    for task in state.plan.tasks:
        progress = progress_by_id[task.task_id]
        print(
            f"{task.task_id}. {task.title} | "
            f"{progress.status.value} | "
            f"{progress.progress_percent:.0f}% | "
            f"{progress.actual_hours_spent:.1f} hours"
        )


def run_session(
    session_name: str,
    management_state: ProjectManagementState,
    work_schedule: WorkSchedule,
    employees,
) -> None:
    """Run the interactive management menu."""

    state_path, schedule_path = session_paths(session_name)
    workflow = build_management_workflow()

    while True:
        print("\n========== LIVE PROJECT MANAGEMENT ==========")
        print("1. Show task progress")
        print("2. Update task progress")
        print("3. Record a task delay")
        print("4. Analyze delay and reschedule")
        print("5. Reassign a task")
        print("6. Generate management report")
        print("7. Save and exit")

        choice = input("Choose an action: ").strip()

        try:
            if choice == "1":
                show_progress(management_state)
                continue

            if choice == "2":
                task_id = int(input("Task ID: "))
                progress_percent = float(
                    input("Progress percentage (0-100): ")
                )
                actual_hours = float(
                    input("Actual hours spent: ")
                )
                status = input(
                    "Status (pending/in_progress/blocked/completed): "
                ).strip().lower()

                result = workflow.invoke({
                    "action": "update_progress",
                    "management_state": management_state,
                    "update_task_id": task_id,
                    "update_task_status": status,
                    "update_progress_percent": progress_percent,
                    "update_actual_hours_spent": actual_hours,
                })

            elif choice == "3":
                task_id = int(input("Task ID: "))
                delay_hours = float(input("Delay in hours: "))
                reason = input("Reason for delay: ").strip()

                result = workflow.invoke({
                    "action": "record_delay",
                    "management_state": management_state,
                    "delay_task_id": task_id,
                    "delay_hours": delay_hours,
                    "delay_reason": reason,
                })


            elif choice == "4":
                task_id = int(input("Delayed task ID: "))
                delay_weeks = int(input("Delay in weeks to apply: "))

                result = workflow.invoke({
                    "action": "analyze_delay",
                    "management_state": management_state,
                    "work_schedule": work_schedule,
                    "employees": employees,
                    "delayed_task_id": task_id,
                    "delay_weeks": delay_weeks,
                })

                impact_report = result.get("schedule_impact_report")
                if impact_report is not None:
                    if hasattr(impact_report, "model_dump"):
                        impact_report = impact_report.model_dump(mode="json")

                    print("\n========== SCHEDULE IMPACT ==========")
                    print(json.dumps(impact_report, indent=2))


            elif choice == "5":
                task_id = int(input("Task ID: "))
                employee_id = input("New employee ID: ").strip()
                reason = input("Reason for reassignment: ").strip()

                result = workflow.invoke({
                    "action": "reassign_task",
                    "management_state": management_state,
                    "employees": employees,
                    "reassign_task_id": task_id,
                    "new_employee_id": employee_id,
                    "reassignment_reason": reason,
                })

            elif choice == "6":
                result = workflow.invoke({
                    "action": "generate_report",
                    "management_state": management_state,
                    "work_schedule": work_schedule,
                })

                report = result["management_report"]
                print("\n========== MANAGEMENT REPORT ==========")
                print(json.dumps(report, indent=2))

                insights = result.get("management_ai_insights")
                if insights is not None:
                    if hasattr(insights, "model_dump"):
                        insights = insights.model_dump(mode="json")
                    print("\n========== GEMINI INSIGHTS ==========")
                    print(json.dumps(insights, indent=2))

                continue

            elif choice == "7":
                print("Management session saved. Goodbye!")
                return

            else:
                print("Invalid option. Choose 1-7.")
                continue

            management_state = result.get(
                "management_state",
                management_state,
            )
            work_schedule = result.get(
                "work_schedule",
                work_schedule,
            )

            # Save both after each successful state-changing action.
            save_management_state(management_state, state_path)
            save_work_schedule(work_schedule, schedule_path)

            print("Action completed. Session state and schedule saved.")

            if "schedule_impact_report" in result:
                impact = result["schedule_impact_report"]
                print("\nSchedule impact:")
                if hasattr(impact, "model_dump"):
                    print(json.dumps(impact.model_dump(mode="json"), indent=2))
                else:
                    print(impact)

        except (ValueError, FileNotFoundError) as error:
            print(f"\nAction could not be completed: {error}")
        except Exception as error:
            print(
                f"\nUnexpected error: {type(error).__name__}: {error}"
            )


def main():
    print("========== AIPlanX LIVE MANAGEMENT ==========")
    print("1. Create a new management session")
    print("2. Resume an existing management session")

    choice = input("Choose an option: ").strip()
    session_name = input(
        "Session name (letters, numbers, _ and - only): "
    ).strip()

    try:
        if choice == "1":
            state, schedule, employees = create_session(session_name)
        elif choice == "2":
            state, schedule, employees = resume_session(session_name)
        else:
            print("Invalid option.")
            return

        run_session(
            session_name=session_name,
            management_state=state,
            work_schedule=schedule,
            employees=employees,
        )

    except Exception as error:
        print(
            f"\nCould not start management session: "
            f"{type(error).__name__}: {error}"
        )


if __name__ == "__main__":
    main()
