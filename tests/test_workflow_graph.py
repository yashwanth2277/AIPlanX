from agents.team_workflow_builder import build_team_workflow
from tests.test_team_workflow_builder import make_plan
from utils.workflow_graph import render_mermaid


def test_mermaid_contains_project_and_tasks():
    workflow = build_team_workflow(make_plan())
    diagram = render_mermaid(workflow)

    assert "flowchart TD" in diagram
    assert "Demo Project" in diagram
    assert "Build API" in diagram
    assert "Test API" in diagram


def test_mermaid_preserves_dependencies():
    workflow = build_team_workflow(make_plan())
    diagram = render_mermaid(workflow)

    assert "task_1 -->|depends on| task_2" in diagram


def test_mermaid_contains_recommended_roles():
    workflow = build_team_workflow(make_plan())
    diagram = render_mermaid(workflow)

    assert "Backend Developer" in diagram
    assert "QA Engineer" in diagram
    assert "class role_backend_developer role" in diagram