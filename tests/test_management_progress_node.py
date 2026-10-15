from agents.management_workflow import update_progress_node
from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
    TaskStatus,
)
from schemas.project_plan import ProjectPlan, Task


def make_management_state():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Demo project",
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
        risks=[],
    )

    return ProjectManagementState(
        plan=plan,
        task_progress=[
            TaskProgress(task_id=1),
            TaskProgress(task_id=2),
        ],
    )


def test_progress_node_updates_task():
    initial_state = make_management_state()

    result = update_progress_node({
        "management_state": initial_state,
        "update_task_id": 1,
        "update_task_status": TaskStatus.IN_PROGRESS,
        "update_progress_percent": 50,
        "update_actual_hours_spent": 2,
    })

    updated = result["management_state"]
    task = next(p for p in updated.task_progress if p.task_id == 1)

    assert task.status == TaskStatus.IN_PROGRESS
    assert task.progress_percent == 50
    assert task.actual_hours_spent == 2


def test_progress_node_preserves_other_tasks_and_original_state():
    initial_state = make_management_state()

    result = update_progress_node({
        "management_state": initial_state,
        "update_task_id": 1,
        "update_task_status": TaskStatus.IN_PROGRESS,
        "update_progress_percent": 25,
        "update_actual_hours_spent": 1,
    })

    updated = result["management_state"]

    assert initial_state.task_progress[0].progress_percent == 0
    assert updated.task_progress[1].status == TaskStatus.PENDING
    assert updated.task_progress[1].progress_percent == 0


def test_progress_node_rejects_completion_with_incomplete_dependency():
    initial_state = make_management_state()

    try:
        update_progress_node({
            "management_state": initial_state,
            "update_task_id": 2,
            "update_task_status": TaskStatus.COMPLETED,
            "update_progress_percent": 100,
            "update_actual_hours_spent": 4,
        })
    except ValueError as exc:
        assert "dependency 1 is not completed" in str(exc)
    else:
        raise AssertionError(
            "Expected incomplete dependency to prevent task completion"
        )