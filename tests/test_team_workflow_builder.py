
from schemas.project_plan import ProjectPlan
from schemas.employee import Employee
from schemas.assignment import AssignmentReport, TaskAssignment
from agents.team_workflow_builder import build_team_workflow


def make_plan():
    return ProjectPlan(
        project_name="Demo Project",
        project_summary="Test team workflow",
        total_estimated_hours=12,
        tasks=[
            {
                "task_id": 1,
                "title": "Build API",
                "description": "Create backend endpoints",
                "required_skills": ["Python", "FastAPI"],
                "estimated_hours": 8,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Test API",
                "description": "Test API endpoints",
                "required_skills": ["pytest", "testing"],
                "estimated_hours": 4,
                "priority": "Medium",
                "dependencies": [1],
            },
        ],
    )


def test_role_based_workflow_without_employees():
    workflow = build_team_workflow(make_plan())

    assert workflow.mode == "role_based"
    assert any(node.node_type == "role" for node in workflow.nodes)
    assert not any(node.node_type == "employee" for node in workflow.nodes)


def test_employee_based_workflow():
    employee = Employee(
        employee_id="E1",
        employee_name="Alex",
        role="Backend Developer",
        skills=["Python", "FastAPI"],
        experience=3,
        current_workload_percent=20,
        weekly_capacity_hours=40,
    )

    assignments = AssignmentReport(
        assignments=[
            TaskAssignment(
                task_id=1,
                task_title="Build API",
                employee_id="E1",
                employee_name="Alex",
                match_score=0.9,
                assignment_reason="Matched Python and FastAPI",
            )
        ]
    )

    workflow = build_team_workflow(
        make_plan(),
        employees=[employee],
        assignments=assignments,
    )

    assert workflow.mode == "employee_based"
    assert any(node.employee_id == "E1" for node in workflow.nodes)
    assert any(node.node_type == "role" for node in workflow.nodes)


def test_task_dependencies_are_preserved():
    workflow = build_team_workflow(make_plan())

    assert any(
        edge.source == "task_1"
        and edge.target == "task_2"
        and edge.relationship == "depends_on"
        for edge in workflow.edges
    )
