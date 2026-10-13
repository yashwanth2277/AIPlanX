from agents.progress_tracker import track_project_progress
from schemas.project_plan import ProjectPlan

from agents.workflow import (
    build_project_workflow,
    validate_workflow_structure,
)
from schemas.resource_allocation import (
    ResourceAllocation,
    ResourceAssignment,
)
from schemas.risk_analysis import RiskAnalysis, ProjectRisk
from schemas.progress_tracking import ProgressReport

def test_workflow_compiles():
    workflow = build_project_workflow()
    assert workflow is not None


def test_workflow_has_all_agents():
    workflow = build_project_workflow()
    graph = workflow.get_graph()

    expected_nodes = {
        "planner",
        "task_breakdown",
        "risk_analysis",
        "schedule_estimation",
        "resource_allocation",
        "progress_tracking",
        "recommendations",
        "final_report",
    }

    assert expected_nodes.issubset(set(graph.nodes.keys()))


def test_workflow_has_correct_connections():
    workflow = build_project_workflow()
    graph = workflow.get_graph()

    actual_edges = {
        (edge.source, edge.target)
        for edge in graph.edges
    }

    expected_edges = {
        ("__start__", "planner"),
        ("planner", "task_breakdown"),
        ("task_breakdown", "risk_analysis"),
        ("risk_analysis", "schedule_estimation"),
        ("schedule_estimation", "resource_allocation"),
        ("resource_allocation", "progress_tracking"),
        ("progress_tracking", "recommendations"),
        ("recommendations", "final_report"),
        ("final_report", "__end__"),
    }

    assert expected_edges.issubset(actual_edges)

def test_progress_tracker_without_api():
    plan = ProjectPlan(
        project_name="Demo Project",
        project_summary="A small demo project",
        total_estimated_hours=6.0,
        tasks=[
            {
                "task_id": 1,
                "title": "Build backend",
                "description": "Create the backend API",
                "required_skills": ["Python", "FastAPI"],
                "estimated_hours": 4.0,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Build frontend",
                "description": "Create the frontend UI",
                "required_skills": ["React", "JavaScript"],
                "estimated_hours": 2.0,
                "priority": "Medium",
                "dependencies": [1],
            },
        ],
    )

    report = track_project_progress(
        plan=plan,
        completed_task_ids=[1],
        actual_hours={1: 4.0, 2: 1.0},
    )

    assert report.completed_tasks == 1
    assert report.pending_tasks == 1
    assert report.overall_progress_percentage == 75.0
    assert report.task_progress[0].status == "Completed"
    assert report.task_progress[1].status == "In Progress"


def test_progress_tracker_rejects_unknown_task_id():
    plan = ProjectPlan(
        project_name="Demo Project",
        project_summary="A small demo project",
        total_estimated_hours=2.0,
        tasks=[
            {
                "task_id": 1,
                "title": "Build backend",
                "description": "Create the backend API",
                "required_skills": ["Python", "FastAPI"],
                "estimated_hours": 2.0,
                "priority": "High",
                "dependencies": [],
            },
        ],
    )

    import pytest

    with pytest.raises(ValueError, match="Unknown task IDs"):
        track_project_progress(
            plan=plan,
            completed_task_ids=[99],
            actual_hours={},
        )

def test_resource_allocation_covers_all_tasks():
    plan = ProjectPlan(
        project_name="Demo Project",
        project_summary="A small demo project",
        total_estimated_hours=3.0,
        tasks=[
            {
                "task_id": 1,
                "title": "Build backend",
                "description": "Create the backend API",
                "required_skills": ["Python", "FastAPI"],
                "estimated_hours": 2.0,
                "priority": "High",
                "dependencies": [],
            },
            {
                "task_id": 2,
                "title": "Build frontend",
                "description": "Create the frontend UI",
                "required_skills": ["React", "JavaScript"],
                "estimated_hours": 1.0,
                "priority": "Medium",
                "dependencies": [1],
            },
        ],
    )

    allocation = ResourceAllocation(
        project_name=plan.project_name,
        assignments=[
            ResourceAssignment(
                task_id=1,
                required_skills=["Python", "FastAPI"],
                recommended_role="Backend Developer",
                estimated_effort_hours=2.0,
                notes="Build the API",
            ),
            ResourceAssignment(
                task_id=2,
                required_skills=["React", "JavaScript"],
                recommended_role="Frontend Developer",
                estimated_effort_hours=1.0,
                notes="Build the UI",
            ),
        ],
        resource_recommendations=["Assign developers based on skills."],
    )

    assigned_task_ids = {
        assignment.task_id for assignment in allocation.assignments
    }
    planned_task_ids = {task.task_id for task in plan.tasks}

    assert assigned_task_ids == planned_task_ids

def test_recommendation_agent_input_schemas():
    risk_analysis = RiskAnalysis(
        project_name="Demo Project",
        overall_risk_level="Medium",
        risks=[
            ProjectRisk(
                risk_id=1,
                title="Schedule delay",
                description="A dependency may delay delivery.",
                severity="Medium",
                mitigation="Review milestones weekly.",
            )
        ],
        recommendations=["Monitor dependencies."],
    )

    progress_report = ProgressReport(
        project_name="Demo Project",
        overall_progress_percentage=50.0,
        completed_tasks=1,
        pending_tasks=1,
        delayed_tasks=[],
        task_progress=[
            {
                "task_id": 1,
                "task_title": "Build backend",
                "planned_hours": 2.0,
                "actual_hours": 2.0,
                "status": "Completed",
                "progress_percentage": 100.0,
                "blockers": [],
            },
            {
                "task_id": 2,
                "task_title": "Build frontend",
                "planned_hours": 2.0,
                "actual_hours": 0.0,
                "status": "Pending",
                "progress_percentage": 0.0,
                "blockers": [],
            },
        ],
        recommendations=["Continue tracking progress."],
    )

    assert risk_analysis.project_name == progress_report.project_name
    assert len(risk_analysis.risks) == 1
    assert progress_report.overall_progress_percentage == 50.0
