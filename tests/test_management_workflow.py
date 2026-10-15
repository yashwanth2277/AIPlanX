from agents.management_workflow import build_management_workflow
from schemas.project_plan import ProjectPlan, Task
from schemas.project_management import ProjectManagementState, TaskStatus
from schemas.assignment import TaskAssignment
from schemas.employee import Employee

def test_management_workflow_has_initializer_node():
    workflow = build_management_workflow()
    graph = workflow.get_graph()

    assert "initialize_management" in graph.nodes


def test_management_workflow_has_start_and_end_edges():
    workflow = build_management_workflow()
    graph = workflow.get_graph()

    edges = {
        (edge.source, edge.target)
        for edge in graph.edges
    }

    assert ("__start__", "initialize_management") in edges
    assert ("initialize_management", "__end__") in edges


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

    assert len(updated_state.task_progress) == 1
    assert updated_state.task_progress[0].task_id == 1
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

    assert initial_state.task_progress[0].progress_percent == 0

def test_management_workflow_generates_report():
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

    management_state = ProjectManagementState(
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
        "action": "generate_report",
        "management_state": management_state,
    })

    report = result["management_report"]

    assert report["project_name"] == "Demo"
    assert report["progress"]["total_tasks"] == 1
    assert report["progress"]["in_progress_tasks"] == 1
    assert report["progress"]["completed_tasks"] == 0
    assert report["task_statuses"]["1"] == "in_progress"
    assert report["recommendations"]

def test_management_workflow_reassigns_task_and_records_history():
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
            )
        ],
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
        assignments=[
            TaskAssignment(
                task_id=1,
                task_title="Build API",
                employee_id="E1",
                employee_name="Alice",
                match_score=0.9,
                assignment_reason="Original assignment",
            )
        ],
    )

    employees = [
        Employee(
            employee_id="E1",
            employee_name="Alice",
            role="Developer",
            skills=["Python"],
            experience=3,
            current_workload_percent=20,
            weekly_capacity_hours=40,
        ),
        Employee(
            employee_id="E2",
            employee_name="Bob",
            role="Developer",
            skills=["Python"],
            experience=4,
            current_workload_percent=20,
            weekly_capacity_hours=40,
        ),
    ]

    workflow = build_management_workflow()

    result = workflow.invoke({
        "action": "reassign_task",
        "management_state": initial_state,
        "employees": employees,
        "reassign_task_id": 1,
        "new_employee_id": "E2",
        "reassignment_reason": "Balance team workload",
    })

    updated_state = result["management_state"]
    assignment = updated_state.assignments[0]
    change = updated_state.assignment_changes[0]
    progress = updated_state.task_progress[0]

    assert assignment.employee_id == "E2"
    assert assignment.employee_name == "Bob"
    assert change.previous_employee_id == "E1"
    assert change.new_employee_id == "E2"
    assert change.reason == "Balance team workload"

    # Reassignment must preserve existing task progress.
    assert progress.status == TaskStatus.IN_PROGRESS
    assert progress.progress_percent == 50
    assert progress.actual_hours_spent == 2

    # The original state must remain unchanged.
    assert initial_state.assignments[0].employee_id == "E1"
    assert initial_state.assignment_changes == []
