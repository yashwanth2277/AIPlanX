
import json
from pathlib import Path

from schemas.final_report import FinalProjectReport

REPORT_PATH = Path("final_report.json")


def main():
    data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    plan = data["project_plan"]
    tasks = plan["tasks"]

    task6 = next(
        (task for task in tasks if task["task_id"] == 6),
        None,
    )
    task11 = next(
        (task for task in tasks if task["task_id"] == 11),
        None,
    )

    if task6 is None:
        raise ValueError("Task 6 was not found.")

    if task11 is not None:
        raise ValueError(
            "Task 11 already exists. No changes were made."
        )

    if task6["estimated_hours"] not in (18, 28, 10):
        raise ValueError(
        "   Task 6 has an unexpected hour estimate."
        )
    backup_path = REPORT_PATH.with_suffix(".json.bak")
    if not backup_path.exists():
        backup_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    # Frontend integration: Sneha's listed skills.
    task6.update({
        "title": "Frontend Integration with Backend API",
        "description": (
            "Connect React UI components to prepared API endpoints. "
            "Handle data fetching, error handling, and UI state."
        ),
        "required_skills": ["React", "JavaScript"],
        "estimated_hours": 10.0,
        "dependencies": [5, 11],
    })

    # Backend integration support: Rahul's listed skills.
    backend_task = {
        "task_id": 11,
        "title": "Backend Integration Support",
        "description": (
            "Prepare and verify FastAPI endpoint contracts and "
            "consistent responses for frontend integration."
        ),
        "required_skills": ["Python", "FastAPI"],
        "estimated_hours": 8.0,
        "priority": "Medium",
        "dependencies": [3, 4],
    }

    task6_index = tasks.index(task6)
    tasks.insert(task6_index + 1, backend_task)

    # Testing must wait for both integration work packages.

    # Testing must wait for both integration work packages.
    task7 = next(
        (task for task in tasks if task["task_id"] == 7),
        None,
    )
    if task7 is None:
        raise ValueError("Task 7 was not found.")

    task7["dependencies"] = sorted(
        set(task7["dependencies"]) | {11}
    )

    # Recalculate the project total after splitting Task 6.
    plan["total_estimated_hours"] = sum(
        task["estimated_hours"] for task in tasks
    )

    # Validate the entire report before writing it.
    validated = FinalProjectReport.model_validate(data)


    if abs(
        validated.project_plan.total_estimated_hours
        - sum(
            task.estimated_hours
            for task in validated.project_plan.tasks
        )
    ) > 0.01:
        raise ValueError("Project hour total is inconsistent.")

    REPORT_PATH.write_text(
        validated.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print("Task 6 split completed successfully.")
    print("Task 6: Frontend integration — 10 hours")
    print("Task 11: Backend integration support — 8 hours")
    print("Task 7 now depends on Task 11 as well.")
    print(
    f"Updated project total: "
    f"{validated.project_plan.total_estimated_hours} hours."
    )
    print(f"Backup: {backup_path.resolve()}")


if __name__ == "__main__":
    main()
