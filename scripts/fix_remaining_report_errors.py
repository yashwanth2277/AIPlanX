
import json
import shutil
from pathlib import Path
from datetime import datetime

from schemas.final_report import FinalProjectReport

REPORT = Path("final_report.json")


def main():
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    tasks = data["project_plan"]["tasks"]
    task_by_id = {task["task_id"]: task for task in tasks}

    if 6 not in task_by_id or 11 not in task_by_id:
        raise ValueError("Task 6 or Task 11 is missing from the plan.")

    # Backup before modifying anything.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = REPORT.with_name(
        f"final_report_before_final_fix_{timestamp}.json"
    )
    shutil.copy2(REPORT, backup)

    # Preserve existing schedule entries for unaffected tasks.
    old_schedule = {
        item["task_id"]: item
        for item in data["schedule"]["scheduled_tasks"]
    }

    # Preserve the current schedule where possible.
    # Task 11 must finish before Task 6 starts.
    old_schedule[11] = {
        "task_id": 11,
        "title": task_by_id[11]["title"],
        "estimated_hours": 8.0,
        "start_day": 8,
        "end_day": 8,
        "dependencies": [3, 4],
    }

    # Task 6 depends on both Task 5 and Task 11.
    # Task 5 currently finishes on day 11.
    old_schedule[6] = {
        "task_id": 6,
        "title": task_by_id[6]["title"],
        "estimated_hours": 10.0,
        "start_day": 12,
        "end_day": 13,
        "dependencies": [5, 11],
    }

    # Task 7 must begin after Tasks 5, 6, and 11 finish.
    old_schedule[7]["dependencies"] = [3, 5, 6, 11]
    old_schedule[7]["start_day"] = 14
    old_schedule[7]["end_day"] = 16

    # Shift downstream deployment to follow testing.
    old_schedule[8]["start_day"] = 17
    old_schedule[8]["end_day"] = 19

    # Documentation depends on Tasks 5 and 6.
    old_schedule[9]["dependencies"] = [5, 6]
    old_schedule[9]["start_day"] = 14
    old_schedule[9]["end_day"] = 15

    data["schedule"]["scheduled_tasks"] = [
        old_schedule[task["task_id"]]
        for task in tasks
    ]
    data["schedule"]["total_duration_days"] = max(
        item["end_day"]
        for item in data["schedule"]["scheduled_tasks"]
    )

    # Keep the existing critical path if valid; Task 11 may be
    # needed in the path depending on the resulting durations.
    data["schedule"]["critical_path"] = [1, 2, 3, 5, 6, 7, 8]

    # Preserve unaffected resource assignments.
    old_resources = {
        item["task_id"]: item
        for item in data["resource_allocation"]["assignments"]
    }

    old_resources[6] = {
        "task_id": 6,
        "required_skills": task_by_id[6]["required_skills"],
        "recommended_role": "Frontend Developer",
        "estimated_effort_hours": 10.0,
        "notes": "Integrate React UI components with the prepared API endpoints.",
    }

    old_resources[11] = {
        "task_id": 11,
        "required_skills": task_by_id[11]["required_skills"],
        "recommended_role": "Backend Developer",
        "estimated_effort_hours": 8.0,
        "notes": "Verify FastAPI endpoint contracts and response consistency.",
    }

    data["resource_allocation"]["assignments"] = [
        old_resources[task["task_id"]]
        for task in tasks
    ]

    # Validate the report's Pydantic structure before saving.
    validated = FinalProjectReport.model_validate(data)
    temp = REPORT.with_suffix(".json.tmp")
    temp.write_text(
        validated.model_dump_json(indent=2),
        encoding="utf-8",
    )
    temp.replace(REPORT)

    print("Targeted repair saved.")
    print(f"Backup: {backup}")
    print(f"Schedule duration: {data['schedule']['total_duration_days']} days")


if __name__ == "__main__":
    main()
