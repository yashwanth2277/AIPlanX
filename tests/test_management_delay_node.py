
from agents.management_workflow import (
    build_management_workflow,
)
from schemas.project_management import (
    ProjectManagementState,
    TaskProgress,
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


def test_management_workflow_records_delay():
    initial_state = make_management_state()

    workflow = build_management_workflow()

    result = workflow.invoke({
        "action": "record_delay",
        "management_state": initial_state,
        "delay_task_id": 1,
        "delay_hours": 8.0,
        "delay_reason": "Dependency delayed",
    })

    updated_state = result["management_state"]

    delay = updated_state.task_progress[0].delays[0]

    assert delay.delay_hours == 8.0
    assert delay.reason == "Dependency delayed"


def test_record_delay_preserves_original_state():
    initial_state = make_management_state()

    workflow = build_management_workflow()

    result = workflow.invoke({
        "action": "record_delay",
        "management_state": initial_state,
        "delay_task_id": 1,
        "delay_hours": 8.0,
        "delay_reason": "Dependency delayed",
    })

    updated_state = result["management_state"]

    assert initial_state.task_progress[0].delays == []
    assert len(updated_state.task_progress[0].delays) == 1


def test_record_delay_rejects_unknown_task():
    initial_state = make_management_state()

    workflow = build_management_workflow()

    try:
        workflow.invoke({
            "action": "record_delay",
            "management_state": initial_state,
            "delay_task_id": 99,
            "delay_hours": 8.0,
            "delay_reason": "Dependency delayed",
        })
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError for an unknown task ID"
        )
