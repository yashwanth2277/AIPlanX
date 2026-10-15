
import pytest
from pydantic import ValidationError

from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
    TaskStatus,
)
from schemas.project_plan import ProjectPlan


def make_plan():
    return ProjectPlan(
        project_name="Demo",
        project_summary="Test project",
        total_estimated_hours=5,
        tasks=[
            {
                "task_id": 1,
                "title": "Build API",
                "description": "Implement API",
                "required_skills": ["Python"],
                "estimated_hours": 5,
                "priority": "High",
                "dependencies": [],
            }
        ],
    )


def test_completed_task_requires_100_percent():
    with pytest.raises(ValidationError):
        TaskProgress(
            task_id=1,
            status=TaskStatus.COMPLETED,
            progress_percent=80,
        )


def test_100_percent_progress_requires_completed_status():
    with pytest.raises(ValidationError):
        TaskProgress(
            task_id=1,
            status=TaskStatus.IN_PROGRESS,
            progress_percent=100,
        )


def test_project_state_requires_progress_for_every_task():
    state = ProjectManagementState(
        plan=make_plan(),
        task_progress=[TaskProgress(task_id=1)],
    )

    assert len(state.task_progress) == 1


def test_project_state_rejects_duplicate_progress_records():
    with pytest.raises(ValidationError):
        ProjectManagementState(
            plan=make_plan(),
            task_progress=[
                TaskProgress(task_id=1),
                TaskProgress(task_id=1),
            ],
        )
