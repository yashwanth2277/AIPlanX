from agents.management_workflow import build_management_workflow
from schemas.project_plan import ProjectPlan, Task
from schemas.project_management import ProjectManagementState, TaskStatus


def test_management_workflow_has_both_nodes():
    graph = build_management_workflow().get_graph()

    assert "initialize_management" in graph.nodes
    assert "update_progress" in graph.nodes


def test_management_workflow_has_both_action_routes():
    graph = build_management_workflow().get_graph()

    edges = {
        (edge.source, edge.target)
        for edge in graph.edges
    }

    assert ("__start__", "initialize_management") in edges
    assert ("__start__", "update_progress") in edges
    assert ("initialize_management", "__end__") in edges
    assert ("update_progress", "__end__") in edges


def test_management_workflow_executes_initializer():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Demo project",
        total_estimated_hours=4,
        tasks=[
            Task(
                task_id=1,
                title="Build API",
                description="Create API",
                required_skills=["Python"],
                estimated_hours=4,
                priority="high",
                dependencies=[],
            )
        ],
        risks=[],
    )

    initial_state = ProjectManagementState(
        plan=plan,
        task_progress=[
            {
                "task_id": 1,
                "status": TaskStatus.IN_PROGRESS,
                "progress_percent": 50,
                "actual_hours_spent": 2,
            }
        ],
    )

    workflow = build_management_workflow()
    result = workflow.invoke({
        "action": "initialize",
        "management_state": initial_state,
    })

    updated_state = result["management_state"]

    assert updated_state.task_progress[0].status == TaskStatus.PENDING
    assert updated_state.task_progress[0].progress_percent == 0


def test_management_workflow_updates_progress_without_resetting():
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

    initial_state = ProjectManagementState(
        plan=plan,
        task_progress=[
            {
                "task_id": 1,
                "status": TaskStatus.PENDING,
                "progress_percent": 0,
                "actual_hours_spent": 0,
            },
            {
                "task_id": 2,
                "status": TaskStatus.IN_PROGRESS,
                "progress_percent": 25,
                "actual_hours_spent": 1,
            },
        ],
    )

    workflow = build_management_workflow()
    result = workflow.invoke({
        "action": "update_progress",
        "management_state": initial_state,
        "update_task_id": 1,
        "update_task_status": TaskStatus.IN_PROGRESS,
        "update_progress_percent": 50,
        "update_actual_hours_spent": 2,
    })

    updated_state = result["management_state"]
    progress = {p.task_id: p for p in updated_state.task_progress}

    assert progress[1].status == TaskStatus.IN_PROGRESS
    assert progress[1].progress_percent == 50
    assert progress[1].actual_hours_spent == 2

    assert progress[2].status == TaskStatus.IN_PROGRESS
    assert progress[2].progress_percent == 25
    assert progress[2].actual_hours_spent == 1

    # Updating the returned state must not mutate the original.
    assert initial_state.task_progress[0].progress_percent == 0
    # SAVE_TEST