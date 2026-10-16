from pathlib import Path

from schemas.final_report import FinalProjectReport
from utils.employee_parser import parse_employee_csv
from utils.work_scheduler import build_work_schedule
from utils.schedule_persistence import (
    save_work_schedule,
    load_work_schedule,
)

report_path = Path("final_report.json")
schedule_path = Path("management_sessions/demo/work_schedule.json")
backup_path = Path("management_sessions/demo/work_schedule.json.bak")

# Validate inputs before changing the saved schedule.
report = FinalProjectReport.model_validate_json(
    report_path.read_text(encoding="utf-8")
)
employees = parse_employee_csv("employees.csv").employees

# Build a fresh schedule using the corrected scheduler.
new_schedule = build_work_schedule(
    plan=report.project_plan,
    employees=employees,
)

# Confirm that every scheduled dependency finishes before its
# dependent task starts.
plan_tasks = {
    task.task_id: task
    for task in report.project_plan.tasks
}
scheduled_tasks = {
    task.task_id: task
    for task in new_schedule.scheduled_tasks
}

for task_id, scheduled in scheduled_tasks.items():
    for dependency_id in plan_tasks[task_id].dependencies:
        if dependency_id not in scheduled_tasks:
            raise ValueError(
                f"Task {task_id} depends on unscheduled task "
                f"{dependency_id}"
            )

        dependency = scheduled_tasks[dependency_id]
        if scheduled.start_week <= dependency.completion_week:
            raise ValueError(
                f"Invalid dependency: task {task_id} starts in week "
                f"{scheduled.start_week}, but task {dependency_id} "
                f"finishes in week {dependency.completion_week}"
            )

# Save only after validation succeeds.
save_work_schedule(new_schedule, schedule_path)

# Verify that the persisted schedule can be loaded.
saved_schedule = load_work_schedule(schedule_path)

print("Schedule rebuilt and validated.")
print(f"Scheduled tasks: {len(saved_schedule.scheduled_tasks)}")
print(f"Unscheduled tasks: {len(saved_schedule.unscheduled_tasks)}")
print(f"Backup retained at: {backup_path}")
print("\nTask schedule:")

for task in sorted(
    saved_schedule.scheduled_tasks,
    key=lambda item: (item.start_week, item.task_id),
):
    print(
        f"Task {task.task_id}: Week {task.start_week}"
        f"-{task.completion_week} | {task.task_title}"
    )

print("\nUnscheduled tasks:")
for task in saved_schedule.unscheduled_tasks:
    print(f"Task {task.get('task_id')}: {task.get('reason')}")
