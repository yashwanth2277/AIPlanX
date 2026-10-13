
import json
from pathlib import Path

from schemas.final_report import FinalProjectReport


def test_task_split_has_correct_hours_skills_and_dependencies():
    data = json.loads(
        Path("final_report.json").read_text(encoding="utf-8")
    )
    report = FinalProjectReport.model_validate(data)

    tasks = {
        task.task_id: task
        for task in report.project_plan.tasks
    }

    # Frontend integration: Task 6
    frontend = tasks[6]
    assert frontend.estimated_hours == 10
    assert set(frontend.required_skills) == {"React", "JavaScript"}
    assert set(frontend.dependencies) == {5, 11}

    # Backend integration support: Task 11
    backend = tasks[11]
    assert backend.estimated_hours == 8
    assert set(backend.required_skills) == {"Python", "FastAPI"}
    assert set(backend.dependencies) == {3, 4}

    # Testing must wait for the backend integration support.
    testing = tasks[7]
    assert 11 in testing.dependencies

    # Project total must match the sum of task hours.
    assert sum(
        task.estimated_hours for task in tasks.values()
    ) == report.project_plan.total_estimated_hours
