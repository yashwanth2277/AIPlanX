
import pytest

from schemas.assignment import TaskAssignment
from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
    TaskStatus,
)
from schemas.project_plan import ProjectPlan
from utils.project_management_engine import (
    record_task_delay,
    update_task_progress,
)


@pytest.fixture
def state():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Test project",
        total_estimated_hours=8,
        tasks=[
            {
                "task_id": 1,
                "title": "Build API",
                "description": "Implement API",
                "required_skills": ["Python"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Build UI",
                "description": "Implement UI",
                "required_skills": ["React"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [1],
            },
        ],
    )

    return ProjectManagementState(
        plan=plan,
        task_progress=[
            TaskProgress(task_id=1),
            TaskProgress(task_id=2),
        ],
    )


def test_update_task_progress(state):
    updated = update_task_progress(
        state,
        task_id=1,
        status=TaskStatus.IN_PROGRESS,
        progress_percent=40,
        actual_hours_spent=2,
    )

    task = next(
        item for item in updated.task_progress
        if item.task_id == 1
    )

    assert task.status == TaskStatus.IN_PROGRESS
    assert task.progress_percent == 40
    assert task.actual_hours_spent == 2

    # The original state must remain unchanged.
    assert state.task_progress[0].progress_percent == 0


def test_cannot_complete_task_before_dependency(state):
    with pytest.raises(ValueError, match="dependency 1"):
        update_task_progress(
            state,
            task_id=2,
            status=TaskStatus.COMPLETED,
            progress_percent=100,
        )


def test_unknown_task_is_rejected(state):
    with pytest.raises(ValueError, match="Unknown task ID"):
        update_task_progress(
            state,
            task_id=999,
            status=TaskStatus.IN_PROGRESS,
            progress_percent=20,
        )


def test_record_delay(state):
    updated = record_task_delay(
        state,
        task_id=1,
        delay_hours=3,
        reason="Waiting for API credentials",
    )

    task = updated.task_progress[0]

    assert len(task.delays) == 1
    assert task.delays[0].delay_hours == 3
    assert task.delays[0].reason == "Waiting for API credentials"
    assert state.task_progress[0].delays == []


def test_invalid_delay_is_rejected(state):
    with pytest.raises(ValueError):
        record_task_delay(
            state,
            task_id=1,
            delay_hours=-2,
            reason="Invalid delay",
        )

def test_progress_above_100_is_rejected(state):
    with pytest.raises(ValueError):
        update_task_progress(
            state,
            task_id=1,
            status=TaskStatus.IN_PROGRESS,
            progress_percent=120,
        )


def test_negative_progress_is_rejected(state):
    with pytest.raises(ValueError):
        update_task_progress(
            state,
            task_id=1,
            status=TaskStatus.IN_PROGRESS,
            progress_percent=-10,
        )


def test_completed_task_cannot_be_updated(state):
    completed_state = update_task_progress(
        state,
        task_id=1,
        status=TaskStatus.COMPLETED,
        progress_percent=100,
        actual_hours_spent=4,
    )

    with pytest.raises(ValueError, match="Completed tasks"):
        update_task_progress(
            completed_state,
            task_id=1,
            status=TaskStatus.IN_PROGRESS,
            progress_percent=50,
        )


def test_delay_for_unknown_task_is_rejected(state):
    with pytest.raises(ValueError, match="Unknown task ID"):
        record_task_delay(
            state,
            task_id=999,
            delay_hours=2,
            reason="Waiting for approval",
        )


def _state_with_assignments():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Test project",
        total_estimated_hours=8,
        tasks=[
            {
                "task_id": 1,
                "title": "Build API",
                "description": "Implement API",
                "required_skills": ["Python"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Build UI",
                "description": "Implement UI",
                "required_skills": ["React"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [1],
            },
        ],
    )

    return ProjectManagementState(
        plan=plan,
        task_progress=[
            TaskProgress(task_id=1),
            TaskProgress(task_id=2),
        ],
        assignments=[
            TaskAssignment(
                task_id=1,
                task_title="Build API",
                employee_id="EMP001",
                employee_name="Rahul",
                match_score=0.9,
                assignment_reason="Python match",
            )
        ],
        applied_delay_ids=["1:existing"],
    )


def test_update_task_progress_preserves_assignments():
    state = _state_with_assignments()

    updated = update_task_progress(
        state,
        task_id=1,
        status=TaskStatus.IN_PROGRESS,
        progress_percent=25,
        actual_hours_spent=1,
    )

    assert len(updated.assignments) == 1
    assert updated.assignments[0].employee_id == "EMP001"
    assert updated.applied_delay_ids == ["1:existing"]


def test_record_task_delay_preserves_assignments():
    state = _state_with_assignments()

    updated = record_task_delay(
        state,
        task_id=1,
        delay_hours=2,
        reason="Waiting for review",
    )

    assert len(updated.assignments) == 1
    assert updated.assignments[0].employee_name == "Rahul"
    assert updated.applied_delay_ids == ["1:existing"]
    assert len(updated.task_progress[0].delays) == 1
