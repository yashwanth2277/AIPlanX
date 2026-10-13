import json

from agents.team_workflow_builder import build_team_workflow
from schemas.project_plan import ProjectPlan
from schemas.resource_allocation import ResourceAllocation
from utils.workflow_graph import render_mermaid


def test_workflow_json_round_trip():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Artifact test",
        total_estimated_hours=4,
        tasks=[
            {
                "task_id": 1,
                "title": "Build API",
                "description": "Implement an API",
                "required_skills": ["Python", "FastAPI"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            }
        ],
    )

    allocation = ResourceAllocation(
        project_name="Demo",
        assignments=[
            {
                "task_id": 1,
                "required_skills": ["Python", "FastAPI"],
                "recommended_role": "Backend Developer",
                "estimated_effort_hours": 4,
                "notes": "Build and validate the API",
            }
        ],
        resource_recommendations=["Allocate backend development capacity"],
    )

    workflow = build_team_workflow(
        plan=plan,
        resource_allocation=allocation,
    )

    restored = json.loads(workflow.model_dump_json())

    assert restored["project_name"] == "Demo"
    assert restored["mode"] == "role_based"
    assert any(
        node["title"] == "Backend Developer"
        for node in restored["nodes"]
    )


def test_diagram_matches_workflow():
    plan = ProjectPlan(
        project_name="Demo",
        project_summary="Diagram test",
        total_estimated_hours=4,
        tasks=[
            {
                "task_id": 1,
                "title": "Build API",
                "description": "Implement an API",
                "required_skills": ["Python", "FastAPI"],
                "estimated_hours": 4,
                "priority": "High",
                "dependencies": [],
            }
        ],
    )

    workflow = build_team_workflow(plan)
    diagram = render_mermaid(workflow)

    assert "Demo" in diagram
    assert "Build API" in diagram
    assert "flowchart TD" in diagram