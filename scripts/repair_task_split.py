
import json
import math
import shutil
from datetime import datetime
from pathlib import Path

from schemas.final_report import FinalProjectReport

REPORT_PATH = Path("final_report.json")
HOURS_PER_DAY = 8


def make_breakdown(task_id, title, parent_hours, subtasks):
    """Create a breakdown whose subtask hours sum to the parent budget."""
    return {
        "task_id": task_id,
        "task_title": title,
        "parent_estimated_hours": float(parent_hours),
        "subtasks": [
            {
                "subtask_id": index,
                "title": subtask_title,
                "description": description,
                "estimated_hours": float(hours),
            }
            for index, (subtask_title, description, hours)
            in enumerate(subtasks, start=1)
        ],
    }


def main():
    if not REPORT_PATH.exists():
        raise FileNotFoundError(REPORT_PATH)

    data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    plan = data["project_plan"]
    tasks = plan["tasks"]
    task_by_id = {task["task_id"]: task for task in tasks}

    if len(task_by_id) != len(tasks):
        raise ValueError("Duplicate task IDs found in project plan.")

    if 6 not in task_by_id or 11 not in task_by_id:
        raise ValueError("Expected Tasks 6 and 11 in the project plan.")

    # 1. Make the dependent sections match the project plan.
    task_by_id[6]["title"] = "Frontend Integration with Backend API"
    task_by_id[11]["title"] = "Backend Integration Support"

    plan["total_estimated_hours"] = sum(
        float(task["estimated_hours"]) for task in tasks
    )

    # 2. Replace Task 6's outdated Admin Dashboard breakdown.
    breakdowns = data["task_breakdowns"]
    breakdown_by_id = {b["task_id"]: b for b in breakdowns}

    if len(breakdown_by_id) != len(breakdowns):
        raise ValueError("Duplicate task breakdowns found.")

    breakdown_by_id[6] = make_breakdown(
        6,
        task_by_id[6]["title"],
        10,
        [
            (
                "Connect frontend API client",
                "Configure API calls and request handling for the required endpoints.",
                3,
            ),
            (
                "Implement response and error handling",
                "Handle API responses, loading states, and errors in React components.",
                4,
            ),
            (
                "Verify frontend integration",
                "Test the integrated UI flows against the prepared backend endpoints.",
                3,
            ),
        ],
    )

    # 3. Add Task 11's breakdown.
    breakdown_by_id[11] = make_breakdown(
        11,
        task_by_id[11]["title"],
        8,
        [
            (
                "Verify API contracts",
                "Confirm request fields, response formats, and endpoint behavior.",
                3,
            ),
            (
                "Standardize backend responses",
                "Check validation and consistent success and error responses.",
                3,
            ),
            (
                "Verify integration readiness",
                "Run endpoint checks and document integration requirements.",
                2,
            ),
        ],
    )

    # Preserve the existing order and append a breakdown for any missing task.
    data["task_breakdowns"] = [
        breakdown_by_id[task["task_id"]]
        for task in tasks
        if task["task_id"] in breakdown_by_id
    ]

    # 4. Build a dependency-respecting schedule.
    # Duration is estimated as ceil(hours / 8) working days.
    durations = {
        task["task_id"]: max(
            1, math.ceil(float(task["estimated_hours"]) / HOURS_PER_DAY)
        )
        for task in tasks
    }

    start_days = {}
    end_days = {}
    remaining = {task["task_id"]: task for task in tasks}

    while remaining:
        progressed = False

        for task_id, task in list(remaining.items()):
            dependencies = task.get("dependencies", [])

            missing = set(dependencies) - set(task_by_id)
            if missing:
                raise ValueError(
                    f"Task {task_id} has missing dependencies: {missing}"
                )

            if not all(dep in end_days for dep in dependencies):
                continue

            start = max(
                (end_days[dep] + 1 for dep in dependencies),
                default=1,
            )
            start_days[task_id] = start
            end_days[task_id] = start + durations[task_id] - 1

            del remaining[task_id]
            progressed = True

        if not progressed:
            raise ValueError(
                "Cannot schedule tasks: dependency cycle detected."
            )

    scheduled_tasks = []
    for task in tasks:
        task_id = task["task_id"]
        scheduled_tasks.append(
            {
                "task_id": task_id,
                "title": task["title"],
                "estimated_hours": float(task["estimated_hours"]),
                "start_day": start_days[task_id],
                "end_day": end_days[task_id],
                "dependencies": list(task.get("dependencies", [])),
            }
        )



    # Calculate the critical path in dependency order.
    longest = {}
    previous = {}
    remaining_tasks = {task["task_id"]: task for task in tasks}

    while remaining_tasks:
        progressed = False

        for task_id, task in list(remaining_tasks.items()):
            deps = task.get("dependencies", [])

            if not all(dep in longest for dep in deps):
                continue

            if deps:
                best_dep = max(deps, key=lambda dep: longest[dep])
                longest[task_id] = longest[best_dep] + durations[task_id]
                previous[task_id] = best_dep
            else:
                longest[task_id] = durations[task_id]
                previous[task_id] = None

            del remaining_tasks[task_id]
            progressed = True

        if not progressed:
            raise ValueError(
                "Cannot calculate critical path: dependency cycle detected."
            )

    last_task = max(longest, key=longest.get)
    critical_path = []
    current = last_task

    while current is not None:
        critical_path.append(current)
        current = previous[current]

    critical_path.reverse()

    # 6. Synchronize progress entries while preserving existing progress.
    progress = data["progress_report"]
    old_progress = {
        item["task_id"]: item
        for item in progress["task_progress"]
    }

    progress_tasks = []

    for task in tasks:
        task_id = task["task_id"]
        old = old_progress.get(task_id, {})

        progress_tasks.append(
            {
                "task_id": task_id,
                "task_title": task["title"],
                "planned_hours": float(task["estimated_hours"]),
                "actual_hours": float(old.get("actual_hours", 0)),
                "status": old.get("status", "Pending"),
                "progress_percentage": float(
                    old.get("progress_percentage", 0)
                ),
                "blockers": old.get("blockers", []),
            }
        )

    progress["task_progress"] = progress_tasks

    # Recalculate task counts from the task statuses.
    progress["completed_tasks"] = sum(
        item["status"].lower() == "completed"
        for item in progress_tasks
    )
    progress["pending_tasks"] = sum(
        item["status"].lower() == "pending"
        for item in progress_tasks
    )

    # 7. Validate the complete Pydantic report before writing anything.
    validated = FinalProjectReport.model_validate(data)
    output = validated.model_dump_json(indent=2)

    # Create a timestamped backup without overwriting previous backups.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = REPORT_PATH.with_name(
        f"final_report_before_repair_{timestamp}.json"
    )
    shutil.copy2(REPORT_PATH, backup_path)

    # Atomic replacement after successful validation.
    temporary_path = REPORT_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(output, encoding="utf-8")
    temporary_path.replace(REPORT_PATH)

    print("Report repair completed.")
    print(f"Tasks: {len(tasks)}")
    print(f"Total estimated hours: {plan['total_estimated_hours']}")
    print(f"Schedule duration: {data['schedule']['total_duration_days']} days")
    print(f"Critical path: {critical_path}")
    print(f"Backup: {backup_path}")


if __name__ == "__main__":
    main()
