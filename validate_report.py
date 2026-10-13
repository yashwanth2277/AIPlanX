
import json

with open("final_report.json", encoding="utf-8") as file:
    report = json.load(file)

plan = report["project_plan"]

planned_ids = {task["task_id"] for task in plan["tasks"]}

checks = {
    "Task breakdown IDs": {
        item["task_id"] for item in report["task_breakdowns"]
    },
    "Scheduled task IDs": {
        item["task_id"] for item in report["schedule"]["scheduled_tasks"]
    },
    "Resource assignment IDs": {
        item["task_id"] for item in report["resource_allocation"]["assignments"]
    },
    "Progress task IDs": {
        item["task_id"] for item in report["progress_report"]["task_progress"]
    },
}

print("Project:", plan["project_name"])

for name, ids in checks.items():
    passed = ids == planned_ids
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        print("  Missing IDs:", sorted(planned_ids - ids))
        print("  Unexpected IDs:", sorted(ids - planned_ids))

calculated_hours = sum(
    task["estimated_hours"] for task in plan["tasks"]
)

print("Planned total hours:", plan["total_estimated_hours"])
print("Calculated total hours:", calculated_hours)
print(
    "Total hours:",
    "PASS" if abs(calculated_hours - plan["total_estimated_hours"]) <= 0.01
    else "FAIL",
)
