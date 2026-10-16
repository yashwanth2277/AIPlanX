import json
from pathlib import Path

from schemas.project_plan import ProjectPlan
from schemas.employee import Employee
from schemas.work_schedule import WorkSchedule
from utils.resource_rescheduler import reschedule_work_schedule
from utils.employee_parser import parse_employee_csv

folder = Path("management_sessions/demo")
state_path = folder / "management_state.json"
schedule_path = folder / "work_schedule.json"

state = json.loads(state_path.read_text(encoding="utf-8"))
schedule_data = json.loads(schedule_path.read_text(encoding="utf-8"))

plan = ProjectPlan.model_validate(state["plan"])
schedule = WorkSchedule.model_validate(schedule_data)
roster = parse_employee_csv("employees.csv")

task_progress = next(
    item for item in state["task_progress"]
    if item["task_id"] == 1
)

total_delay_hours = sum(
    item["delay_hours"] for item in task_progress["delays"]
)

if total_delay_hours != 8:
    raise ValueError(
        f"Expected 8 recorded delay hours, found {total_delay_hours}"
    )

revised_schedule = reschedule_work_schedule(
    plan=plan,
    employees=roster.employees,
    schedule=schedule,
    delayed_task_id=1,
    delay_weeks=1,
)

# Save only the schedule; management progress and delay history stay untouched.
schedule_path.write_text(
    revised_schedule.model_dump_json(indent=2),
    encoding="utf-8",
)

print("Applied one-week demo delay to Task 1.")
print("Recorded delay hours:", total_delay_hours)
print("Management state was not modified.")
print("Revised schedule:")
for task in sorted(
    revised_schedule.scheduled_tasks,
    key=lambda item: (item.start_week, item.task_id),
):
    print(
        f"Task {task.task_id}: "
        f"Week {task.start_week}-{task.completion_week}"
    )