
import pytest

from schemas.project_plan import ProjectPlan, Task
from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
    TaskStatus,
    DelayRecord,
    AssignmentChange,
)
from schemas.assignment import TaskAssignment
from utils.management_persistence import (
    save_management_state,
    load_management_state,
)


def make_management_state():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Persistence test",
        total_estimated_hours=8,
        tasks=[
            Task(
                task_id=1,
                title="Build API",
                description="Create API",
                required_skills=["Python"],
                estimated_hours=4,
                priority="high",
                dependencies=[],
            ),
            Task(
                task_id=2,
                title="Build UI",
                description="Create UI",
                required_skills=["JavaScript"],
                estimated_hours=4,
                priority="medium",
                dependencies=[1],
            ),
        ],
        risks=["Possible API integration delay"],
    )

    return ProjectManagementState(
        plan=plan,
        task_progress=[
            TaskProgress(
                task_id=1,
                status=TaskStatus.IN_PROGRESS,
                progress_percent=50,
                actual_hours_spent=3,
                delays=[
                    DelayRecord(
                        task_id=1,
                        delay_hours=2,
                        reason="API integration blocked",
                    )
                ],
            ),
            TaskProgress(
                task_id=2,
                status=TaskStatus.PENDING,
                progress_percent=0,
                actual_hours_spent=0,
            ),
        ],
        assignments=[
            TaskAssignment(
                task_id=1,
                task_title="Build API",
                employee_id="E1",
                employee_name="Alice",
                match_score=0.9,
                assignment_reason="Matched Python skills",
            )
        ],
        assignment_changes=[
            AssignmentChange(
                task_id=1,
                previous_employee_id="E2",
                new_employee_id="E1",
                reason="Rebalanced workload",
            )
        ],
    )


def test_save_and_load_preserves_management_state(tmp_path):
    original = make_management_state()
    file_path = tmp_path / "projects" / "demo.json"

    save_management_state(original, file_path)
    restored = load_management_state(file_path)

    assert restored == original
    assert restored.task_progress[0].progress_percent == 50
    assert restored.task_progress[0].delays[0].delay_hours == 2
    assert restored.assignments[0].employee_id == "E1"
    assert restored.assignment_changes[0].previous_employee_id == "E2"


def test_load_missing_file_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_management_state(tmp_path / "missing.json")


def test_load_invalid_json_raises_error(tmp_path):
    file_path = tmp_path / "invalid.json"
    file_path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid management state JSON"):
        load_management_state(file_path)


def test_load_invalid_management_data_raises_error(tmp_path):
    file_path = tmp_path / "invalid_state.json"
    file_path.write_text('{"unexpected": "data"}', encoding="utf-8")

    with pytest.raises(ValueError, match="Management state data is invalid"):
        load_management_state(file_path)
