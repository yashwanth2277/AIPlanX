
import json
from pathlib import Path

report_path = Path("final_report.json")
data = json.loads(report_path.read_text(encoding="utf-8"))

tasks = {
    task["task_id"]: task
    for task in data["project_plan"]["tasks"]
}

for breakdown in data["task_breakdowns"]:
    task_id = breakdown["task_id"]

    if task_id not in tasks:
        raise ValueError(f"No parent task found for task {task_id}")

    parent_hours = float(tasks[task_id]["estimated_hours"])
    subtasks = breakdown["subtasks"]

    if not subtasks:
        raise ValueError(f"Task {task_id} has no subtasks")

    original_total = sum(
        float(subtask["estimated_hours"])
        for subtask in subtasks
    )

    if original_total <= 0:
        raise ValueError(f"Task {task_id} has invalid subtask hours")

    # Scale estimates proportionally and round to 2 decimals.
    remaining = parent_hours

    for subtask in subtasks[:-1]:
        scaled = round(
            float(subtask["estimated_hours"])
            * parent_hours
            / original_total,
            2,
        )
        subtask["estimated_hours"] = scaled
        remaining -= scaled

    # Use the remainder to ensure the sum matches the parent exactly.
    subtasks[-1]["estimated_hours"] = round(remaining, 2)
    breakdown["parent_estimated_hours"] = parent_hours

    print(
        f"Task {task_id}: {original_total}h -> "
        f"{sum(s['estimated_hours'] for s in subtasks)}h "
        f"(budget {parent_hours}h)"
    )

report_path.write_text(
    json.dumps(data, indent=2),
    encoding="utf-8",
)

print("Subtask estimates updated.")
